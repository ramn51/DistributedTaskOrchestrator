#  Copyright 2026 Ram Narayanan
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0

"""
research_subtopic.py — Titan worker script for the Research Pipeline example.

Runs on a Titan worker node. Receives a subtopic assignment, calls Gemini to
research it, and stores the result in TitanStore so the downstream synthesis
job can retrieve it.

Args: <run_id> <subtopic_index>

Requires:
    pip install google-genai python-dotenv

Environment:
    GEMINI_API_KEY — your Gemini API key
    TITAN_HOST     — Master host (default: 127.0.0.1)
    TITAN_PORT     — Master port (default: 9090)
"""

import sys
import os
import socket
import struct
from dotenv import load_dotenv
load_dotenv()

# ── Titan KV helpers (raw protocol — no titan_sdk dependency needed on worker) ─
TITAN_HOST = os.environ.get("TITAN_HOST", "127.0.0.1")
TITAN_PORT = int(os.environ.get("TITAN_PORT", "9090"))
VERSION    = 1
OP_KV_SET  = 0x60
OP_KV_GET  = 0x61


def _titan_send(op, payload):
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(10)
        s.connect((TITAN_HOST, TITAN_PORT))
        body   = payload.encode("utf-8")
        header = struct.pack(">BBBBI", VERSION, op, 0, 0, len(body))
        s.sendall(header + body)
        raw = b""
        while len(raw) < 8:
            chunk = s.recv(8 - len(raw))
            if not chunk:
                break
            raw += chunk
        if len(raw) < 8:
            return ""
        _, _, _, _, rlen = struct.unpack(">BBBBI", raw)
        if rlen == 0:
            return ""
        data = b""
        while len(data) < rlen:
            chunk = s.recv(min(rlen - len(data), 4096))
            if not chunk:
                break
            data += chunk
        return data.decode("utf-8", errors="ignore")
    except Exception as e:
        return f"ERROR: {e}"
    finally:
        if s:
            try:
                s.close()
            except Exception:
                pass


def kv_set(key, value):
    return _titan_send(OP_KV_SET, f"{key}|{value}")


def kv_get(key):
    return _titan_send(OP_KV_GET, key).strip()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 3:
        print("Usage: research_subtopic.py <run_id> <subtopic_index>", flush=True)
        sys.exit(1)

    run_id = sys.argv[1]
    idx    = int(sys.argv[2])

    # Read config from TitanStore (written by the orchestrator before submission)
    topic    = kv_get(f"titan:research:{run_id}:topic")
    subtopic = kv_get(f"titan:research:{run_id}:subtopic:{idx}")

    if not topic or topic.startswith("ERROR"):
        print(f"[ERROR] Could not retrieve topic from TitanStore. run_id={run_id}", flush=True)
        sys.exit(1)
    if not subtopic or subtopic.startswith("ERROR"):
        print(f"[ERROR] Could not retrieve subtopic {idx}. run_id={run_id}", flush=True)
        sys.exit(1)

    print("=" * 60, flush=True)
    print(f"[RESEARCH] Worker starting — subtopic {idx}", flush=True)
    print(f"[RESEARCH] Main topic : {topic}", flush=True)
    print(f"[RESEARCH] Subtopic   : {subtopic}", flush=True)
    print("=" * 60, flush=True)

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("[ERROR] 'google-genai' package not installed.", flush=True)
        print("[ERROR] Fix: pip install google-genai", flush=True)
        sys.exit(1)

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY environment variable not set.", flush=True)
        sys.exit(1)

    prompt = (
        f"You are a research analyst producing a section of a larger report.\n\n"
        f"Main Topic: {topic}\n"
        f"Your Section: {subtopic}\n\n"
        f"Write a focused, 3-paragraph research summary covering:\n"
        f"1. Current state and key facts\n"
        f"2. Notable trends or recent developments\n"
        f"3. Implications and near-term outlook\n\n"
        f"Be factual, insightful, and use concrete examples. "
        f"Avoid filler phrases. Aim for ~200 words."
    )

    print(f"[RESEARCH] Calling Gemini API for subtopic {idx}...", flush=True)

    gemini = genai.Client(api_key=api_key)
    response = gemini.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.4)
    )

    result = response.text.strip()
    input_tokens  = getattr(getattr(response, "usage_metadata", None), "prompt_token_count", 0)
    output_tokens = getattr(getattr(response, "usage_metadata", None), "candidates_token_count", 0)

    # Store result in TitanStore so synthesize_report.py can read it
    kv_set(f"titan:research:{run_id}:result:{idx}", result)
    kv_set(f"titan:research:{run_id}:status:{idx}", "DONE")

    print(f"[RESEARCH] Complete — {input_tokens} in / {output_tokens} out tokens", flush=True)
    print(f"\n--- Result Preview ---", flush=True)
    print(result[:250] + ("..." if len(result) > 250 else ""), flush=True)
    print(f"----------------------\n", flush=True)
    print(f"[RESEARCH] Stored in TitanStore: titan:research:{run_id}:result:{idx}", flush=True)


if __name__ == "__main__":
    main()
