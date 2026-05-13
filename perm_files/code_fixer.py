#  Copyright 2026 Ram Narayanan
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0

"""
code_fixer.py — Code Generation Agent: Fixer stage.

Reads the review decision and component code content from TitanStore, calls
Gemini to fix the specific issue, and writes the fixed code back to TitanStore
under the same key — so the reviewer and integrator always see the latest version.

Args: <run_id> <review_iteration> <issue_idx>

Requires: pip install google-genai python-dotenv
"""

import sys
import os
import json
from dotenv import load_dotenv

load_dotenv()


def main():
    if len(sys.argv) < 4:
        print("Usage: code_fixer.py <run_id> <review_iteration> <issue_idx>", flush=True)
        sys.exit(1)

    run_id           = sys.argv[1]
    review_iteration = int(sys.argv[2])
    issue_idx        = int(sys.argv[3])

    from titan_sdk import TitanClient
    tc = TitanClient()

    # Read review decision from TitanStore
    review_json = tc.store_get(f"code:{run_id}:review:{review_iteration}")
    if not review_json or review_json in ("NULL", "CLEARED"):
        print(f"[ERROR] Review not found in TitanStore for iteration {review_iteration}.", flush=True)
        sys.exit(1)

    review = json.loads(review_json)
    issues = review.get("issues", [])

    if issue_idx >= len(issues):
        print(f"[ERROR] Issue idx={issue_idx} out of range ({len(issues)} issues).", flush=True)
        sys.exit(1)

    issue          = issues[issue_idx]
    component_idx  = issue["component_idx"]
    component_name = issue["component_name"]
    problem        = issue["problem"]
    fix_hint       = issue.get("fix_hint", "")

    print("=" * 60, flush=True)
    print(f"[FIXER-{review_iteration}-{issue_idx}] Component: {component_name}", flush=True)
    print(f"[FIXER-{review_iteration}-{issue_idx}] Problem  : {problem}", flush=True)
    print(f"[FIXER-{review_iteration}-{issue_idx}] Fix hint : {fix_hint}", flush=True)
    print("=" * 60, flush=True)

    # Read component code content from TitanStore
    existing_code = tc.store_get(f"code:{run_id}:component:{component_idx}:content")
    if not existing_code or existing_code in ("NULL", "CLEARED"):
        print(f"[ERROR] Component content not found in TitanStore for idx {component_idx}.", flush=True)
        sys.exit(1)

    # Read goal from plan in TitanStore
    plan_json = tc.store_get(f"code:{run_id}:plan")
    goal = json.loads(plan_json)["goal"] if plan_json and plan_json not in ("NULL", "CLEARED") else ""

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY not set.", flush=True)
        sys.exit(1)

    from google import genai
    from google.genai import types

    prompt = f"""You are an expert Python developer fixing a specific issue in a code module.

Overall system goal: "{goal}"
Module: {component_name}

Current code:
```python
{existing_code}
```

Issue identified by code reviewer:
  Problem  : {problem}
  Fix hint : {fix_hint}

Fix ONLY this specific issue. Do not refactor unrelated parts of the code.
Preserve all existing functionality that is correct.

Return ONLY the complete fixed Python code, no markdown fences, no explanation."""

    client   = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.2)
    )

    fixed_code = response.text.strip()
    if fixed_code.startswith("```"):
        lines = fixed_code.split("\n")
        fixed_code = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    header = f"# Component: {component_name}\n# Fixed: review_iteration {review_iteration}, issue {issue_idx}\n\n"
    full_fixed = header + fixed_code

    # Write fixed code back to TitanStore under the same key —
    # reviewer and integrator always read the latest version from here
    try:
        tc.store_put(f"code:{run_id}:component:{component_idx}:content", full_fixed)
        tc.store_put(f"code:{run_id}:fixer:{review_iteration}:{issue_idx}:done", "1")
        print(f"[FIXER-{review_iteration}-{issue_idx}] Fixed code stored in TitanStore ({len(fixed_code)} chars).", flush=True)
    except Exception as e:
        print(f"[FIXER-{review_iteration}-{issue_idx}] TitanStore signal skipped: {e}", flush=True)


if __name__ == "__main__":
    main()
