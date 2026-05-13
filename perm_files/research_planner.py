#  Copyright 2026 Ram Narayanan
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0

"""
research_planner.py — Agentic Research Agent: Planner stage.

Receives a research query, calls Gemini to break it into focused subtopics,
and stores the plan JSON in TitanStore for downstream workers to consume.

Args: <run_id> <query_with_underscores>

Requires: pip install google-genai python-dotenv
"""

import sys
import os
import json
from dotenv import load_dotenv

load_dotenv()


def main():
    if len(sys.argv) < 3:
        print("Usage: research_planner.py <run_id> <query>", flush=True)
        sys.exit(1)

    run_id = sys.argv[1]
    query  = " ".join(sys.argv[2:]).replace("_", " ")

    # CWD = titan_workspace/shared (set by ScriptExecutorHandler for DAG jobs)

    print("=" * 60, flush=True)
    print(f"[PLANNER] Research query: {query}", flush=True)
    print("=" * 60, flush=True)

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY not set.", flush=True)
        sys.exit(1)

    from google import genai
    from google.genai import types

    prompt = f"""You are a research director planning a deep-dive investigation.

Query: "{query}"

Break this into exactly 4 focused, non-overlapping research subtopics that together would give a complete answer.

Respond with ONLY valid JSON, no markdown, no explanation:
{{"subtopics": ["subtopic 1", "subtopic 2", "subtopic 3", "subtopic 4"]}}"""

    client   = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2
        )
    )

    plan = json.loads(response.text)
    subtopics = plan.get("subtopics", [])

    print(f"[PLANNER] Subtopics decided:", flush=True)
    for i, s in enumerate(subtopics):
        print(f"  [{i}] {s}", flush=True)

    # Write plan file to CWD (= titan_workspace/shared)
    plan_filename = f"research_{run_id}_plan.json"
    with open(plan_filename, "w") as f:
        json.dump({"query": query, "subtopics": subtopics}, f, indent=2)

    # Store plan JSON and file path in TitanStore
    try:
        from titan_sdk import TitanClient
        tc = TitanClient()
        tc.store_put(f"research:{run_id}:plan", json.dumps({"query": query, "subtopics": subtopics}))
        tc.store_put(f"research:{run_id}:plan:path", os.path.abspath(plan_filename))
        tc.store_put(f"research:{run_id}:planner:done", "1")
        print(f"[PLANNER] Plan stored in TitanStore and written to {os.path.abspath(plan_filename)}", flush=True)
    except Exception as e:
        print(f"[PLANNER] TitanStore signal skipped: {e}", flush=True)


if __name__ == "__main__":
    main()
