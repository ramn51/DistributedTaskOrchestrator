#  Copyright 2026 Ram Narayanan
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0

"""
research_evaluator.py — Agentic Research Agent: Evaluator stage.

THE AGENTIC STEP. Fetches all research result files from the master
(uploaded by researchers via OP_UPLOAD_ASSET), calls Gemini to judge
whether the research is sufficient, and stores the routing decision
directly in TitanStore: SYNTHESIZE (done) or DEEPEN (gaps, loop again).

Args: <run_id> <iteration> <query_with_underscores>

Requires: pip install google-genai python-dotenv
"""

import sys
import os
import json
from dotenv import load_dotenv

load_dotenv()


def main():
    if len(sys.argv) < 4:
        print("Usage: research_evaluator.py <run_id> <iteration> <query>", flush=True)
        sys.exit(1)

    run_id    = sys.argv[1]
    iteration = int(sys.argv[2])
    query     = " ".join(sys.argv[3:]).replace("_", " ")

    print("=" * 60, flush=True)
    print(f"[EVALUATOR] Iteration {iteration} — evaluating research quality", flush=True)
    print(f"[EVALUATOR] Query: {query}", flush=True)
    print("=" * 60, flush=True)

    from titan_sdk import TitanClient
    tc = TitanClient()

    # Fetch all result files published by researchers
    sections = []
    for it in range(1, iteration + 1):
        idx = 0
        while True:
            local_path = f"result_{it}_{idx}.txt"
            if not tc.get_artifact(f"research:{run_id}:result:{it}:{idx}", save_path=local_path):
                break
            with open(local_path) as f:
                content = f.read()
            lines    = content.split("\n", 3)
            subtopic = lines[0].replace("SUBTOPIC:", "").strip() if lines else "Unknown"
            text     = lines[3].strip() if len(lines) > 3 else content
            sections.append((subtopic, text))
            print(f"[EVALUATOR]   Fetched: {subtopic} ({len(text)} chars)", flush=True)
            idx += 1

    if not sections:
        print("[ERROR] No research results found.", flush=True)
        sys.exit(1)

    research_block = "\n\n---\n\n".join(
        f"Subtopic: {name}\n{text}" for name, text in sections
    )

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY not set.", flush=True)
        sys.exit(1)

    from google import genai
    from google.genai import types

    prompt = f"""You are a research quality evaluator.

Original query: "{query}"

Research collected so far:
{research_block}

Evaluate whether this research is sufficient to write a complete, high-quality answer to the query.

If the research is sufficient (covers the query well with enough depth and breadth):
  Return: {{"decision": "SYNTHESIZE"}}

If there are clear gaps that would leave the query partially unanswered (max 2 gaps):
  Return: {{"decision": "DEEPEN", "gaps": ["specific gap 1", "specific gap 2"]}}

Be strict: only recommend DEEPEN if there is a genuinely important aspect missing.
If research is reasonably complete, choose SYNTHESIZE.

Respond with ONLY valid JSON, no markdown, no explanation."""

    print(f"\n[EVALUATOR] Calling Gemini to assess research quality...", flush=True)

    client   = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1
        )
    )

    decision = json.loads(response.text)

    print(f"[EVALUATOR] Decision: {decision['decision']}", flush=True)
    if decision.get("gaps"):
        for g in decision["gaps"]:
            print(f"[EVALUATOR]   Gap: {g}", flush=True)

    # Store decision JSON directly in TitanStore
    try:
        tc.store_put(f"research:{run_id}:eval:{iteration}", json.dumps(decision))
        tc.store_put(f"research:{run_id}:eval:{iteration}:done", "1")
        print(f"[EVALUATOR] Decision stored in TitanStore.", flush=True)
    except Exception as e:
        print(f"[EVALUATOR] TitanStore signal skipped: {e}", flush=True)


if __name__ == "__main__":
    main()
