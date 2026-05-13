#  Copyright 2026 Ram Narayanan
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0

"""
synthesize_report.py — Titan worker script for the Research Pipeline example.

Fan-in synthesis stage. Reads all subtopic research results from TitanStore
(written by the parallel research_subtopic.py workers), calls Gemini to
synthesize a final professional report, and saves it as a Markdown file.

Args: <run_id>

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

# ── Titan KV helpers ───────────────────────────────────────────────────────────
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
    if len(sys.argv) < 2:
        print("Usage: synthesize_report.py <run_id>", flush=True)
        sys.exit(1)

    run_id = sys.argv[1]

    topic = kv_get(f"titan:research:{run_id}:topic")
    count_str = kv_get(f"titan:research:{run_id}:count")

    if not topic or topic.startswith("ERROR"):
        print(f"[ERROR] Could not retrieve topic. run_id={run_id}", flush=True)
        sys.exit(1)
    if not count_str or count_str.startswith("ERROR"):
        print(f"[ERROR] Could not retrieve subtopic count. run_id={run_id}", flush=True)
        sys.exit(1)

    count = int(count_str)
    print("=" * 60, flush=True)
    print(f"[SYNTHESIS] Starting synthesis for: '{topic}'", flush=True)
    print(f"[SYNTHESIS] Gathering {count} research sections...", flush=True)
    print("=" * 60, flush=True)

    # Collect all subtopic research results from TitanStore
    sections = []
    missing  = []
    for i in range(count):
        subtopic = kv_get(f"titan:research:{run_id}:subtopic:{i}")
        result   = kv_get(f"titan:research:{run_id}:result:{i}")
        status   = kv_get(f"titan:research:{run_id}:status:{i}")

        if result and not result.startswith("ERROR") and status == "DONE":
            sections.append((subtopic, result))
            print(f"[SYNTHESIS]   [{i}] '{subtopic}' — {len(result)} chars  ✓", flush=True)
        else:
            missing.append(i)
            print(f"[SYNTHESIS]   [{i}] '{subtopic}' — MISSING or ERROR  ✗", flush=True)

    if not sections:
        print("[ERROR] No research sections available. Cannot synthesize.", flush=True)
        sys.exit(1)

    if missing:
        print(f"[WARN] {len(missing)} subtopic(s) missing — synthesizing with available data.", flush=True)

    # Build the combined research context for Claude
    research_block = "\n\n---\n\n".join(
        f"### Section {i+1}: {name}\n\n{text}"
        for i, (name, text) in enumerate(sections)
    )

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
        f"You are a senior research analyst. Your team has investigated the following topic "
        f"from multiple angles. Synthesize their work into a single, polished research report.\n\n"
        f"Topic: {topic}\n\n"
        f"RESEARCH SECTIONS:\n\n{research_block}\n\n"
        f"Write a structured report with these sections:\n"
        f"1. **Executive Summary** — 3 sentences capturing the most important takeaways.\n"
        f"2. **Key Findings** — 5 bullet points. Each should be a concrete, specific insight.\n"
        f"3. **Analysis** — Integrate the research sections into a cohesive narrative. "
        f"Highlight connections between sections. ~300 words.\n"
        f"4. **Conclusion & Outlook** — What this means in the next 12-24 months.\n\n"
        f"Format in clean Markdown. Be authoritative, avoid repetition, "
        f"and prioritize insight over summary."
    )

    print(f"\n[SYNTHESIS] Calling Gemini for final synthesis...", flush=True)

    gemini = genai.Client(api_key=api_key)
    response = gemini.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.2)
    )

    report        = response.text.strip()
    input_tokens  = getattr(getattr(response, "usage_metadata", None), "prompt_token_count", 0)
    output_tokens = getattr(getattr(response, "usage_metadata", None), "candidates_token_count", 0)

    print(f"[SYNTHESIS] Synthesis complete — {input_tokens} in / {output_tokens} out tokens", flush=True)

    # Store in TitanStore (truncated to fit KV value limits)
    kv_set(f"titan:research:{run_id}:report", report[:4000])

    # Write full report to local file in the worker workspace
    safe_topic = "".join(c if c.isalnum() or c in " _-" else "_" for c in topic)
    safe_topic = safe_topic.replace(" ", "_")[:40]
    filename   = f"research_report_{safe_topic}_{run_id[:8]}.md"

    with open(filename, "w") as f:
        f.write(f"# Research Report: {topic}\n\n")
        f.write(f"*Generated by Titan Research Pipeline · Run ID: `{run_id}`*\n\n")
        f.write(f"---\n\n")
        f.write(report)
        f.write(f"\n\n---\n\n")
        f.write(f"*Sections researched: {', '.join(name for name, _ in sections)}*\n")

    print(f"[SYNTHESIS] Report saved → {filename}", flush=True)
    print(f"\n{'=' * 60}", flush=True)
    # Stream the report to the dashboard log viewer
    for line in report.split("\n"):
        print(line, flush=True)
    print(f"{'=' * 60}\n", flush=True)


if __name__ == "__main__":
    main()
