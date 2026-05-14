#  Copyright 2026 Ram Narayanan
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0

"""
research_pipeline.py — Multi-Agent Research Pipeline orchestrator.

Stage 1: Planner (Gemini) decides subtopics at runtime — the DAG shape is
         not known until this stage completes.
Stage 2: N parallel research workers fan out across the cluster (N determined
         by the planner, not hardcoded).
Stage 3: HITL gate — human approves or rejects before synthesis runs.
Stage 4: Synthesizer fans in all results into a final Markdown report.

The agentic element is the Planner: it decides how many subtopics to research
and what they are. The orchestrator cannot build the research DAG until the
planner has run — making this a genuinely dynamic pipeline.

Usage:
    python research_pipeline.py
    python research_pipeline.py "Quantum computing in finance"

Requires:
    pip install google-genai python-dotenv
    GEMINI_API_KEY in .env or shell

Dashboard:
    http://localhost:5000
"""

import sys
import os
import time
import uuid

# Worker scripts live alongside this orchestrator
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))

_PLANNER_SCRIPT    = os.path.join(_HERE, "pipeline_planner.py")
_RESEARCH_SCRIPT   = os.path.join(_HERE, "research_subtopic.py")
_SYNTHESIZE_SCRIPT = os.path.join(_HERE, "synthesize_report.py")
_HITL_GATE_SCRIPT  = os.path.join(_HERE, "hitl_gate.py")

for _f in (_PLANNER_SCRIPT, _RESEARCH_SCRIPT, _SYNTHESIZE_SCRIPT, _HITL_GATE_SCRIPT):
    if not os.path.exists(_f):
        print(f"[ERROR] Required script not found: {_f}")
        sys.exit(1)

# ── Titan KV helpers (write config before submitting the DAG) ─────────────────
# ── SDK ───────────────────────────────────────────────────────────────────────
try:
    from titan_sdk import TitanClient, TitanJob
except ImportError:
    print("[ERROR] titan_sdk not found. Install with: pip install -e .")
    sys.exit(1)


DEFAULT_TOPIC  = "The future of AI agents in software engineering"
POLL_INTERVAL  = 2
POLL_TIMEOUT   = 180


def wait_for_signal(client, key, label, timeout=POLL_TIMEOUT):
    deadline = time.time() + timeout
    while time.time() < deadline:
        val = client.store_get(key)
        if val and val not in ("NULL", "CLEARED"):
            print(f"[PIPELINE]   {label} — done", flush=True)
            return True
        time.sleep(POLL_INTERVAL)
    print(f"[PIPELINE]   {label} — TIMED OUT", flush=True)
    return False


def main():
    topic  = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TOPIC
    run_id = uuid.uuid4().hex[:12]
    tag    = run_id[:6]

    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║           Titan Multi-Agent Research Pipeline            ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"  Topic     : {topic}")
    print(f"  Run ID    : {run_id}")
    print(f"  Dashboard : http://localhost:5000")
    print()

    client = TitanClient()

    # ── Stage 1: Write topic to TitanStore, run Planner ───────────────────────
    # Planner decides subtopics at runtime — the research DAG cannot be built
    # until this stage completes.
    client.store_put(f"titan:research:{run_id}:topic", topic)

    print("[PIPELINE] Stage 1 — Planner: deciding subtopics...", flush=True)
    planner_job = TitanJob(
        job_id      = f"pipeline-planner-{tag}",
        filename    = _PLANNER_SCRIPT,
        args        = run_id,
        requirement = "GENERAL",
        priority    = 5,
    )
    client.submit_dag(f"PIPELINE_{tag}_PLAN", [planner_job], agent_run_id=run_id)

    if not wait_for_signal(client, f"titan:research:{run_id}:planner:done", label="planner"):
        print("[ERROR] Planner timed out.", flush=True)
        sys.exit(1)

    # Read subtopics decided by the planner
    count     = int(client.store_get(f"titan:research:{run_id}:count") or 0)
    subtopics = [client.store_get(f"titan:research:{run_id}:subtopic:{i}") for i in range(count)]

    print(f"[PIPELINE] Planner decided {count} subtopics:", flush=True)
    for i, s in enumerate(subtopics):
        print(f"  [{i}] {s}", flush=True)

    # ── Stage 2-4: Build and submit the research DAG dynamically ──────────────
    # N is now determined by the planner — not hardcoded or from CLI args.
    research_jobs = [
        TitanJob(
            job_id      = f"research-{i}",
            filename    = _RESEARCH_SCRIPT,
            args        = f"{run_id} {i}",
            requirement = "GENERAL",
            priority    = 5,
        )
        for i in range(count)
    ]

    gate_job = TitanJob(
        job_id   = "research-review",
        filename = _HITL_GATE_SCRIPT,
        args     = (
            f"research-review 3600 "
            f"Planner decided {count} subtopics for '{topic}'. "
            f"Research complete — approve to synthesize the final report."
        ),
        parents  = [f"research-{i}" for i in range(count)],
        priority = 5,
    )

    synthesis_job = TitanJob(
        job_id   = "synthesize",
        filename = _SYNTHESIZE_SCRIPT,
        args     = run_id,
        parents  = ["research-review"],
        priority = 8,
    )

    all_jobs = research_jobs + [gate_job, synthesis_job]

    print(f"\n[PIPELINE] Stage 2 — Submitting {count} parallel researchers + HITL + synthesizer...", flush=True)
    result = client.submit_dag(f"PIPELINE_{tag}_RESEARCH", all_jobs, agent_run_id=run_id)
    print(f"[PIPELINE] Master response: {result}", flush=True)

    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  Pipeline running! What happens next:                   ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║  {count} research workers running in parallel on the cluster  ")
    print( "║                                                          ║")
    print( "║  When all finish, the HITL gate activates:             ║")
    print( "║  → Dashboard → DAG Pipelines                           ║")
    print( "║  → Click [Approve] to generate the final report        ║")
    print( "║  → Click [Reject]  to halt the pipeline                ║")
    print( "║                                                          ║")
    print(f"║  Dashboard → http://localhost:5000                       ║")
    print( "╚══════════════════════════════════════════════════════════╝")
    print()


if __name__ == "__main__":
    main()
