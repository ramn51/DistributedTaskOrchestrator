#  Copyright 2026 Ram Narayanan
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0

"""
Competitive Intelligence Pipeline — Titan Agentic Example
==========================================================

Demonstrates:
  - Dynamic fan-out: N parallel analyst agents, one per framework
  - Shared workspace filesystem for reliable inter-agent data passing
  - Fan-in synthesis: one agent depends on ALL analysts completing
  - Live log streaming per agent in the Dashboard

Architecture:
  Orchestrator
      │  calls submit_dag() with all config passed as CLI args
      ▼
  Titan Master
      ├── analyst-0  (framework, topic as args)  →  Gemini  →  shared/intel_<run_id>_result_0.txt
      ├── analyst-1  (framework, topic as args)  →  Gemini  →  shared/intel_<run_id>_result_1.txt
      └── analyst-2  (framework, topic as args)  →  Gemini  →  shared/intel_<run_id>_result_2.txt
               │  (all three complete)
               ▼
          synthesizer (run_id, count, fw names as args)
               →  reads result files
               →  Gemini
               →  shared/comp_intel_<fws>_<run_id>.md

Usage:
  # Default: LangGraph vs CrewAI vs AutoGen
  python comp_intel_pipeline.py

  # Custom topic + frameworks
  python comp_intel_pipeline.py "Cloud AI Platforms" "AWS SageMaker" "Google Vertex AI" "Azure ML"

Requires:
  pip install google-genai python-dotenv
  GEMINI_API_KEY in .env or exported in shell
"""

import os
import sys
import uuid
from dotenv import load_dotenv

load_dotenv()

# ── Locate perm_files ──────────────────────────────────────────────────────────
_HERE       = os.path.dirname(os.path.abspath(__file__))
_PERM_FILES = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", "perm_files"))

_ANALYST_SCRIPT     = os.path.join(_PERM_FILES, "comp_intel_analyst.py")
_SYNTHESIZER_SCRIPT = os.path.join(_PERM_FILES, "comp_intel_synthesizer.py")

for _path in [_ANALYST_SCRIPT, _SYNTHESIZER_SCRIPT]:
    if not os.path.exists(_path):
        print(f"[ERROR] Worker script not found: {_path}")
        sys.exit(1)

from titan_sdk import TitanClient, TitanJob

DEFAULT_TOPIC      = "AI Agent Orchestration Frameworks"
DEFAULT_FRAMEWORKS = ["LangGraph", "CrewAI", "AutoGen"]
MAX_FRAMEWORKS     = 6


def run_pipeline():
    args = sys.argv[1:]
    if args:
        topic      = args[0]
        frameworks = args[1:] if len(args) > 1 else DEFAULT_FRAMEWORKS
    else:
        topic      = DEFAULT_TOPIC
        frameworks = DEFAULT_FRAMEWORKS

    if len(frameworks) > MAX_FRAMEWORKS:
        print(f"[WARN] Truncating to {MAX_FRAMEWORKS} frameworks.")
        frameworks = frameworks[:MAX_FRAMEWORKS]

    run_id = uuid.uuid4().hex[:12]
    client = TitanClient()

    print()
    print("=" * 60)
    print("  TITAN — Competitive Intelligence Pipeline")
    print("=" * 60)
    print(f"  Run ID     : {run_id}")
    print(f"  Topic      : {topic}")
    print(f"  Frameworks : {', '.join(frameworks)}")
    print(f"  Analysts   : {len(frameworks)} parallel Gemini agents")
    print("=" * 60)
    print()

    # Each analyst gets: run_id, index, framework_name, topic — all as args
    # No TitanStore dependency for config
    analyst_jobs = [
        TitanJob(
            job_id      = f"analyst-{i}",
            filename    = _ANALYST_SCRIPT,
            args        = f"{run_id} {i} {fw.replace(' ', '_')} {topic.replace(' ', '_')}",
            requirement = "GENERAL",
            priority    = 5,
        )
        for i, fw in enumerate(frameworks)
    ]

    # Synthesizer gets: run_id, count, then framework names (spaces → _)
    synth_args = f"{run_id} {len(frameworks)} " + " ".join(fw.replace(" ", "_") for fw in frameworks)
    synthesizer_job = TitanJob(
        job_id      = "synthesizer",
        filename    = _SYNTHESIZER_SCRIPT,
        args        = synth_args,
        parents     = [f"analyst-{i}" for i in range(len(frameworks))],
        requirement = "GENERAL",
        priority    = 8,
    )

    all_jobs = analyst_jobs + [synthesizer_job]
    client.submit_dag("COMP_INTEL_PIPELINE", all_jobs)

    print(f"[PIPELINE] DAG submitted — {len(all_jobs)} jobs")
    print(f"[PIPELINE] {len(frameworks)} analyst(s) running in parallel...\n")
    print("  Watch it run:")
    print("  → Dashboard : http://localhost:5000")
    print("  → DAG view  : http://localhost:5000/dags\n")
    print(f"  Report will be saved to:")
    print(f"  titan_workspace/shared/comp_intel_*_{run_id[:8]}.md\n")


if __name__ == "__main__":
    run_pipeline()
