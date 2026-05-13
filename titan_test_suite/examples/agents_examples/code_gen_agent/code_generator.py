#  Copyright 2026 Ram Narayanan
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0

"""
code_generator.py — Code Generation Agent: Generator stage.

Reads the plan from TitanStore, generates clean Python code for one component,
and stores the code content directly in TitanStore so the reviewer and fixer
can access it from any node without file transfer.

Args: <run_id> <iteration> <component_idx>

Requires: pip install google-genai python-dotenv
"""

import sys
import os
import json
from dotenv import load_dotenv

load_dotenv()


def main():
    if len(sys.argv) < 4:
        print("Usage: code_generator.py <run_id> <iteration> <component_idx>", flush=True)
        sys.exit(1)

    run_id    = sys.argv[1]
    iteration = int(sys.argv[2])
    idx       = int(sys.argv[3])

    from titan_sdk import TitanClient
    tc = TitanClient()

    # Read plan from TitanStore
    plan_json = tc.store_get(f"code:{run_id}:plan")
    if not plan_json or plan_json in ("NULL", "CLEARED"):
        print(f"[ERROR] Plan not found in TitanStore for run {run_id}", flush=True)
        sys.exit(1)

    plan       = json.loads(plan_json)
    goal       = plan["goal"]
    language   = plan.get("language", "Python")
    components = plan["components"]
    component  = next((c for c in components if c["idx"] == idx), None)
    if not component:
        print(f"[ERROR] Component idx={idx} not found in plan.", flush=True)
        sys.exit(1)

    name        = component["name"]
    description = component["description"]

    print("=" * 60, flush=True)
    print(f"[GENERATOR-{iteration}-{idx}] Component: {name}", flush=True)
    print(f"[GENERATOR-{iteration}-{idx}] Spec: {description[:80]}", flush=True)
    print("=" * 60, flush=True)

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY not set.", flush=True)
        sys.exit(1)

    from google import genai
    from google.genai import types

    other_components = [c for c in components if c["idx"] != idx]
    context = "\n".join(
        f"  - {c['name']}: {c['description']}" for c in other_components
    )

    prompt = f"""You are an expert {language} developer writing one module of a larger system.

Overall goal: "{goal}"

Your module: {name}
Specification: {description}

Other modules in the system (write compatible interfaces):
{context}

Write clean, well-structured {language} code for the {name} module.
Requirements:
- Include a module docstring
- Add type hints
- Include clear inline comments for non-obvious logic
- Write practical, working code — not pseudocode
- Make the public interface clean and easy to use by the other modules

Return ONLY the Python code, no markdown fences, no explanation."""

    client   = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.3)
    )

    code = response.text.strip()
    if code.startswith("```"):
        lines = code.split("\n")
        code = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    header = f"# Component: {name}\n# Generated: iteration {iteration}\n\n"
    full_code = header + code

    print(f"[GENERATOR-{iteration}-{idx}] Generated {len(code)} chars", flush=True)
    print("\n".join(code.split("\n")[:8]), flush=True)
    print("...\n", flush=True)

    # Store code content directly in TitanStore — reviewer/fixer read from here,
    # works across any worker node without file transfer
    try:
        tc.store_put(f"code:{run_id}:component:{idx}:content", full_code)
        tc.store_put(f"code:{run_id}:generator:{iteration}:{idx}:done", "1")
        print(f"[GENERATOR-{iteration}-{idx}] Code stored in TitanStore.", flush=True)
    except Exception as e:
        print(f"[GENERATOR-{iteration}-{idx}] TitanStore signal skipped: {e}", flush=True)


if __name__ == "__main__":
    main()
