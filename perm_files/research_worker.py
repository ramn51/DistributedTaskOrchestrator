#  Copyright 2026 Ram Narayanan
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0

"""
research_worker.py — Agentic Research Agent: Researcher stage.

Reads the plan from TitanStore, calls Gemini for an in-depth analysis of
one subtopic, writes the result to CWD (titan_workspace/shared on the worker
node), uploads it to the master via OP_UPLOAD_ASSET, and stores the filename
in TitanStore so the evaluator and synthesizer can fetch it.

Args: <run_id> <iteration> <index> <subtopic_with_underscores>

Requires: pip install google-genai python-dotenv
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()


def main():
    if len(sys.argv) < 5:
        print("Usage: research_worker.py <run_id> <iteration> <index> <subtopic>", flush=True)
        sys.exit(1)

    run_id    = sys.argv[1]
    iteration = int(sys.argv[2])
    idx       = int(sys.argv[3])
    subtopic  = " ".join(sys.argv[4:]).replace("_", " ")

    # CWD = titan_workspace/shared on the worker node

    print("=" * 60, flush=True)
    print(f"[RESEARCHER-{iteration}-{idx}] Subtopic: {subtopic}", flush=True)
    print("=" * 60, flush=True)

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY not set.", flush=True)
        sys.exit(1)

    from google import genai
    from google.genai import types

    prompt = f"""You are a specialist researcher producing one section of a larger report.

Subtopic: {subtopic}

Write a focused, detailed research summary (~250 words) covering:
1. Current state — key facts, numbers, concrete examples
2. Notable developments or trends in the last 1-2 years
3. Key challenges or open problems
4. Practical implications for teams building real systems

Be specific and factual. Avoid vague generalities."""

    client   = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.3)
    )

    result = response.text.strip()

    # Write result file to CWD (worker-local titan_workspace/shared)
    out_filename = f"research_{run_id}_result_{iteration}_{idx}.txt"
    with open(out_filename, "w") as f:
        f.write(f"SUBTOPIC:{subtopic}\nITERATION:{iteration}\n\n")
        f.write(result)

    print(f"[RESEARCHER-{iteration}-{idx}] Done — {len(result)} chars", flush=True)
    print(result[:200] + "...", flush=True)

    # Publish result to master so evaluator/synthesizer (any node) can fetch it
    try:
        from titan_sdk import TitanClient
        tc = TitanClient()
        tc.publish_artifact(f"research:{run_id}:result:{iteration}:{idx}", out_filename)
        tc.store_put(f"research:{run_id}:researcher:{iteration}:{idx}:done", "1")
        print(f"[RESEARCHER-{iteration}-{idx}] TitanStore signal sent.", flush=True)
    except Exception as e:
        print(f"[RESEARCHER-{iteration}-{idx}] TitanStore/upload skipped: {e}", flush=True)


if __name__ == "__main__":
    main()
