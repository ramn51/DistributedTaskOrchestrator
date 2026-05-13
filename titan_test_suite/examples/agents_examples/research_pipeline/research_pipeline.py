#  Copyright 2026 Ram Narayanan
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0

"""
research_pipeline.py — Multi-Agent Research Pipeline orchestrator.

Submits a Titan DAG that:
  1. Fans out N parallel Claude research workers (one per subtopic)
  2. Pauses at a HITL gate so you can review before the final synthesis
  3. Fans back in with Claude Opus to synthesize a polished Markdown report

This example showcases:
  - Dynamic DAG construction (N jobs built from a Python list at runtime)
  - TitanStore as shared agent memory (all workers read topic config, write results)
  - Parallel fan-out / fan-in execution pattern
  - Human-in-the-Loop gate between research and synthesis
  - Live log streaming in the Dashboard

Usage:
    python research_pipeline.py
    python research_pipeline.py "Quantum computing in finance"
    python research_pipeline.py "LLM safety" "Alignment research" "Red-teaming" "Interpretability"

Requires:
    pip install anthropic          # on every worker node
    export ANTHROPIC_API_KEY=...   # on every worker node

Dashboard:
    http://localhost:5000          # watch the parallel workers execute in real time
"""

import sys
import os
import time
import uuid

# ── Locate perm_files relative to this script ─────────────────────────────────
# Layout: titan_test_suite/examples/agents_examples/research_pipeline/
#         → 4 levels up → project root → perm_files/
_HERE      = os.path.dirname(os.path.abspath(__file__))
_ROOT      = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
_PERM      = os.path.join(_ROOT, "perm_files")

_RESEARCH_SCRIPT   = os.path.join(_PERM, "research_subtopic.py")
_SYNTHESIZE_SCRIPT = os.path.join(_PERM, "synthesize_report.py")
_HITL_GATE_SCRIPT  = os.path.join(_PERM, "hitl_gate.py")

for _f in (_RESEARCH_SCRIPT, _SYNTHESIZE_SCRIPT, _HITL_GATE_SCRIPT):
    if not os.path.exists(_f):
        print(f"[ERROR] Required script not found: {_f}")
        print("[ERROR] Make sure you are running from inside the titan-orchestrator repo.")
        sys.exit(1)

# ── Titan KV helpers (write config before submitting the DAG) ─────────────────
# ── SDK ───────────────────────────────────────────────────────────────────────
try:
    from titan_sdk import TitanClient, TitanJob
except ImportError:
    print("[ERROR] titan_sdk not found. Install with: pip install -e .")
    sys.exit(1)


# ── Default research config ────────────────────────────────────────────────────
DEFAULT_TOPIC = "The future of AI agents in software engineering"
DEFAULT_SUBTOPICS = [
    "Current Landscape & State of the Art",
    "Key Technical Challenges",
    "Emerging Patterns & Architectures",
    "Impact on Developer Workflows",
]


def parse_args():
    """
    Accepts optional CLI overrides:
      - First arg   : main topic
      - Remaining   : custom subtopics (minimum 2, maximum 8)
    """
    args = sys.argv[1:]
    if not args:
        return DEFAULT_TOPIC, DEFAULT_SUBTOPICS

    topic = args[0]
    if len(args) > 1:
        subtopics = args[1:]
        if len(subtopics) < 2:
            print("[WARN] Provide at least 2 subtopics. Using defaults.")
            subtopics = DEFAULT_SUBTOPICS
        elif len(subtopics) > 8:
            print("[WARN] Maximum 8 subtopics. Truncating.")
            subtopics = subtopics[:8]
    else:
        subtopics = DEFAULT_SUBTOPICS

    return topic, subtopics


def main():
    topic, subtopics = parse_args()
    run_id = uuid.uuid4().hex[:12]      # short unique ID for this pipeline run

    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║           Titan Multi-Agent Research Pipeline            ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"  Topic     : {topic}")
    print(f"  Subtopics : {len(subtopics)}")
    for i, s in enumerate(subtopics):
        print(f"              [{i}] {s}")
    print(f"  Run ID    : {run_id}")
    print(f"  Dashboard : http://localhost:5000")
    print()

    client = TitanClient()

    # ── Step 1: Write pipeline config to TitanStore ───────────────────────────
    # All worker nodes will read this before calling Claude.
    print("[SETUP] Writing pipeline config to TitanStore...", flush=True)
    client.store_put(f"titan:research:{run_id}:topic", topic)
    client.store_put(f"titan:research:{run_id}:count", str(len(subtopics)))
    for i, subtopic in enumerate(subtopics):
        client.store_put(f"titan:research:{run_id}:subtopic:{i}", subtopic)
    print("[SETUP] Config stored.", flush=True)

    # ── Step 2: Build the DAG ─────────────────────────────────────────────────

    # N parallel research jobs — each runs on any available GENERAL worker
    research_jobs = [
        TitanJob(
            job_id    = f"research-{i}",
            filename  = _RESEARCH_SCRIPT,
            args      = f"{run_id} {i}",
            requirement = "GENERAL",
            priority  = 5,
        )
        for i in range(len(subtopics))
    ]

    # HITL review gate — waits for all research jobs to finish
    # The reviewer sees the Approve/Reject buttons in the Dashboard.
    # Approved → synthesis runs.  Rejected → pipeline halts.
    gate_job = TitanJob(
        job_id   = "research-review",
        filename = _HITL_GATE_SCRIPT,
        args     = (
            f"research-review "
            f"3600 "                     # 1-hour timeout
            f"Research complete: {len(subtopics)} subtopics analyzed for "
            f"'{topic}'. Approve to generate the final report."
        ),
        parents  = [f"research-{i}" for i in range(len(subtopics))],
        priority = 5,
    )

    # Single synthesis job — fans in all results and writes the final report
    synthesis_job = TitanJob(
        job_id   = "synthesize",
        filename = _SYNTHESIZE_SCRIPT,
        args     = run_id,
        parents  = ["research-review"],
        priority = 8,
    )

    all_jobs = research_jobs + [gate_job, synthesis_job]

    # ── Step 3: Submit ────────────────────────────────────────────────────────
    dag_name = f"research-pipeline-{run_id}"
    print(f"\n[SUBMIT] Submitting DAG '{dag_name}' with {len(all_jobs)} jobs...", flush=True)

    result = client.submit_dag(dag_name, all_jobs)
    print(f"[SUBMIT] Master response: {result}", flush=True)

    # ── Step 4: Instructions ──────────────────────────────────────────────────
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  Pipeline submitted! Here is what happens next:         ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║  1. {len(subtopics)} research workers run in parallel on the cluster  ")
    print( "║     Each calls Gemini to research its assigned subtopic. ║")
    print( "║                                                          ║")
    print( "║  2. When all finish, the HITL gate activates.           ║")
    print( "║     → Open the Dashboard → DAG Pipelines                ║")
    print( "║     → Click [Approve] to generate the final report      ║")
    print( "║     → Click [Reject]  to halt the pipeline              ║")
    print( "║                                                          ║")
    print( "║  3. The synthesis job calls Gemini to combine all       ║")
    print( "║     research into a polished Markdown report.           ║")
    print( "║                                                          ║")
    print(f"║  Dashboard → http://localhost:5000                       ║")
    print( "╚══════════════════════════════════════════════════════════╝")
    print()


if __name__ == "__main__":
    main()
