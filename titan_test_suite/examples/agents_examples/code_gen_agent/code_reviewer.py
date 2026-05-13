#  Copyright 2026 Ram Narayanan
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0

"""
code_reviewer.py — Code Generation Agent: Reviewer stage.

THE AGENTIC STEP. Reads plan and all component code content from TitanStore
(stored by generators/fixers), calls Gemini to review code quality and interface
compatibility, then stores the routing decision in TitanStore:
  APPROVE (done) or REQUEST_CHANGES (loop again with targeted fixes).

Args: <run_id> <iteration> <goal_with_underscores>

Requires: pip install google-genai python-dotenv
"""

import sys
import os
import json
from dotenv import load_dotenv

load_dotenv()


def main():
    if len(sys.argv) < 4:
        print("Usage: code_reviewer.py <run_id> <iteration> <goal>", flush=True)
        sys.exit(1)

    run_id    = sys.argv[1]
    iteration = int(sys.argv[2])
    goal      = " ".join(sys.argv[3:]).replace("_", " ")

    print("=" * 60, flush=True)
    print(f"[REVIEWER] Iteration {iteration} — reviewing all components", flush=True)
    print(f"[REVIEWER] Goal: {goal}", flush=True)
    print("=" * 60, flush=True)

    from titan_sdk import TitanClient
    tc = TitanClient()

    # Read plan from TitanStore
    plan_json = tc.store_get(f"code:{run_id}:plan")
    if not plan_json or plan_json in ("NULL", "CLEARED"):
        print(f"[ERROR] Plan not found in TitanStore.", flush=True)
        sys.exit(1)

    plan = json.loads(plan_json)
    components = sorted(plan["components"], key=lambda c: c["idx"])

    # Read each component's code content directly from TitanStore
    code_blocks = []
    for c in components:
        content = tc.store_get(f"code:{run_id}:component:{c['idx']}:content")
        if not content or content in ("NULL", "CLEARED"):
            print(f"[REVIEWER]   No content for component {c['idx']} — skipping", flush=True)
            continue
        code_blocks.append((c["idx"], c["name"], content))
        print(f"[REVIEWER]   Loaded: {c['name']} ({len(content)} chars)", flush=True)

    if not code_blocks:
        print("[ERROR] No component content found in TitanStore.", flush=True)
        sys.exit(1)

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY not set.", flush=True)
        sys.exit(1)

    from google import genai
    from google.genai import types

    code_section = "\n\n---\n\n".join(
        f"### Component {idx}: {name}\n```python\n{code}\n```"
        for idx, name, code in code_blocks
    )

    prompt = f"""You are a senior code reviewer evaluating a multi-component Python codebase.

Overall goal: "{goal}"

Components to review:
{code_section}

Review for:
1. Correctness — does each component do what it should?
2. Interface compatibility — do the components work together cleanly?
3. Code quality — proper error handling, type hints, no obvious bugs?
4. Completeness — is anything critical missing?

If the code is good enough to ship (may have minor style issues but no functional problems):
  Return: {{"decision": "APPROVE"}}

If there are real functional issues that need fixing (max 3 issues, focus on the most important):
  Return: {{
    "decision": "REQUEST_CHANGES",
    "issues": [
      {{"component_idx": 0, "component_name": "name", "problem": "specific problem description", "fix_hint": "what to do"}}
    ]
  }}

Be strict but fair. Only REQUEST_CHANGES for real problems, not style preferences.
Respond with ONLY valid JSON, no markdown."""

    print(f"\n[REVIEWER] Calling Gemini for code review...", flush=True)

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

    print(f"[REVIEWER] Decision: {decision['decision']}", flush=True)
    if decision.get("issues"):
        for issue in decision["issues"]:
            print(f"[REVIEWER]   Issue in {issue['component_name']}: {issue['problem']}", flush=True)

    # Store review decision in TitanStore
    try:
        tc.store_put(f"code:{run_id}:review:{iteration}", json.dumps(decision))
        tc.store_put(f"code:{run_id}:reviewer:{iteration}:done", "1")
        print(f"[REVIEWER] Review stored in TitanStore.", flush=True)
    except Exception as e:
        print(f"[REVIEWER] TitanStore signal skipped: {e}", flush=True)


if __name__ == "__main__":
    main()
