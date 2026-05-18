#  Copyright 2026 Ram Narayanan
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0

"""
comp_intel_analyst.py — Titan worker for the Competitive Intelligence Pipeline.

Runs on a Titan worker node. Receives assignment via CLI args, calls Gemini
to produce a competitive analysis, and writes the result to the shared workspace.

Args: <run_id> <analyst_index> <framework_name> <topic>

Requires:
    pip install google-genai python-dotenv
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()


def main():
    if len(sys.argv) < 5:
        print("Usage: comp_intel_analyst.py <run_id> <index> <framework> <topic>", flush=True)
        sys.exit(1)

    run_id    = sys.argv[1]
    idx       = int(sys.argv[2])
    framework = sys.argv[3].replace("_", " ")
    topic     = sys.argv[4].replace("_", " ")

    print("=" * 60, flush=True)
    print(f"[ANALYST-{idx}] Starting analysis", flush=True)
    print(f"[ANALYST-{idx}] Framework : {framework}", flush=True)
    print(f"[ANALYST-{idx}] Topic     : {topic}", flush=True)
    print("=" * 60, flush=True)

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY not set. Add it to .env or export it.", flush=True)
        sys.exit(1)

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("[ERROR] google-genai not installed. Run: pip install google-genai", flush=True)
        sys.exit(1)

    prompt = f"""You are a senior technology analyst producing a competitive intelligence brief.

Framework Under Analysis: {framework}
Context: {topic}

Write a focused competitive analysis covering these four dimensions:

**1. Architecture & Design Philosophy**
How is it built? What core design decisions define it? (3-4 sentences)

**2. Key Strengths**
What does it do better than alternatives? Give concrete, specific examples. (3-4 bullet points)

**3. Weaknesses & Limitations**
Where does it fall short? What use cases does it handle poorly? Be honest. (3-4 bullet points)

**4. Best Fit Use Cases**
What type of project or team should choose this framework and why? (2-3 sentences)

Be direct, specific, and avoid marketing language. Aim for ~250 words."""

    print(f"[ANALYST-{idx}] Calling Gemini API...", flush=True)

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.3)
    )

    result = response.text.strip()

    # Write result to TitanStore — works across any worker node
    from titan_sdk import TitanClient
    store = TitanClient()
    store.store_put(f"intel_{run_id}_result_{idx}", f"FRAMEWORK:{framework}\n{result}")

    print(f"[ANALYST-{idx}] Analysis complete — {len(result)} chars", flush=True)
    print(f"[ANALYST-{idx}] Saved → TitanStore key: intel_{run_id}_result_{idx}", flush=True)
    print(f"\n--- {framework} Preview ---", flush=True)
    print(result[:300] + ("..." if len(result) > 300 else ""), flush=True)
    print(f"----------------------------\n", flush=True)


if __name__ == "__main__":
    main()
