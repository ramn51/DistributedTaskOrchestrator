#  Copyright 2026 Ram Narayanan
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0

"""
pipeline_planner.py — Planner stage for the Multi-Agent Research Pipeline.

Runs on a Titan worker node. Reads the main topic from TitanStore, calls
Gemini to decide how many subtopics to research and what they are, then
writes the plan back to TitanStore so the orchestrator can build the
downstream DAG dynamically.

This is the agentic element: the orchestrator cannot submit the research
DAG until this worker runs — because only after this call does it know how
many parallel research jobs to create.

Args: <run_id>

Requires:
    pip install google-genai python-dotenv

Environment:
    GEMINI_API_KEY
"""

import sys
import os
import json
import socket
import struct
from dotenv import load_dotenv

load_dotenv()

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


def main():
    if len(sys.argv) < 2:
        print("Usage: pipeline_planner.py <run_id>", flush=True)
        sys.exit(1)

    run_id = sys.argv[1]

    topic = kv_get(f"titan:research:{run_id}:topic")
    if not topic or topic.startswith("ERROR"):
        print(f"[PLANNER] ERROR: Could not read topic from TitanStore.", flush=True)
        sys.exit(1)

    print("=" * 60, flush=True)
    print(f"[PLANNER] Topic: {topic}", flush=True)
    print("=" * 60, flush=True)

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("[PLANNER] ERROR: GEMINI_API_KEY not set.", flush=True)
        sys.exit(1)

    from google import genai
    from google.genai import types

    prompt = f"""You are a research director planning a deep-dive investigation.

Topic: "{topic}"

Decide the right number of focused, non-overlapping subtopics (between 3 and 6) that together give a complete picture of this topic. More complex topics warrant more subtopics.

Respond with ONLY valid JSON, no markdown:
{{"subtopics": ["subtopic 1", "subtopic 2", ...]}}"""

    client   = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2
        )
    )

    plan      = json.loads(response.text)
    subtopics = plan.get("subtopics", [])

    # Clamp to 2–8 just in case the model goes out of range
    subtopics = subtopics[:8]
    if len(subtopics) < 2:
        print(f"[PLANNER] ERROR: Planner returned fewer than 2 subtopics.", flush=True)
        sys.exit(1)

    print(f"[PLANNER] Decided {len(subtopics)} subtopics:", flush=True)
    for i, s in enumerate(subtopics):
        print(f"  [{i}] {s}", flush=True)

    # Write subtopics back to TitanStore — orchestrator reads these to build the DAG
    kv_set(f"titan:research:{run_id}:count", str(len(subtopics)))
    for i, s in enumerate(subtopics):
        kv_set(f"titan:research:{run_id}:subtopic:{i}", s)

    # Signal completion — orchestrator is polling this key
    kv_set(f"titan:research:{run_id}:planner:done", "1")
    print(f"[PLANNER] Plan written to TitanStore. Orchestrator will build DAG.", flush=True)


if __name__ == "__main__":
    main()
