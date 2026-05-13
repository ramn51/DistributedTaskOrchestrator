#  Copyright 2026 Ram Narayanan
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0

"""
code_planner.py — Code Generation Agent: Planner stage.

Receives a coding goal, calls Gemini to decompose it into 3-4 independent
components, writes the plan file to CWD (titan_workspace/shared), and stores
the plan JSON directly in TitanStore for downstream workers to consume.

Args: <run_id> <goal_with_underscores>

Requires: pip install google-genai python-dotenv
"""

import sys
import os
import json
from dotenv import load_dotenv

load_dotenv()


def main():
    if len(sys.argv) < 3:
        print("Usage: code_planner.py <run_id> <goal>", flush=True)
        sys.exit(1)

    run_id = sys.argv[1]
    goal   = " ".join(sys.argv[2:]).replace("_", " ")

    # CWD = titan_workspace/shared (set by ScriptExecutorHandler for DAG jobs)

    print("=" * 60, flush=True)
    print(f"[PLANNER] Goal  : {goal}", flush=True)
    print(f"[PLANNER] Run ID: {run_id}", flush=True)
    print("=" * 60, flush=True)

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY not set.", flush=True)
        sys.exit(1)

    from google import genai
    from google.genai import types

    prompt = f"""You are a software architect decomposing a coding goal into independent components.

Goal: "{goal}"

Break this into exactly 3-4 independent, non-overlapping components that together implement the full goal.
Each component should be a self-contained module a single developer could write independently.

Respond with ONLY valid JSON, no markdown:
{{
  "goal": "{goal}",
  "language": "Python",
  "components": [
    {{"idx": 0, "name": "short_module_name", "description": "what this module does and its public interface"}},
    {{"idx": 1, "name": "short_module_name", "description": "what this module does and its public interface"}},
    {{"idx": 2, "name": "short_module_name", "description": "what this module does and its public interface"}}
  ]
}}"""

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
    components = plan.get("components", [])

    print(f"[PLANNER] Components ({len(components)}):", flush=True)
    for c in components:
        print(f"  [{c['idx']}] {c['name']} — {c['description'][:60]}...", flush=True)

    # Write plan file to CWD (= titan_workspace/shared)
    plan_filename = f"code_{run_id}_plan.json"
    with open(plan_filename, "w") as f:
        json.dump(plan, f, indent=2)

    # Store plan JSON in TitanStore — generators, reviewer, fixer, integrator all read from here
    try:
        from titan_sdk import TitanClient
        tc = TitanClient()
        tc.store_put(f"code:{run_id}:plan", json.dumps(plan))
        tc.store_put(f"code:{run_id}:planner:done", "1")
        print(f"[PLANNER] Plan stored in TitanStore.", flush=True)
    except Exception as e:
        print(f"[PLANNER] TitanStore signal skipped: {e}", flush=True)


if __name__ == "__main__":
    main()
