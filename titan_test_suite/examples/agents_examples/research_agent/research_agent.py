#  Copyright 2026 Ram Narayanan
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0

"""
Research Agent — Titan Agentic Example
=======================================

A planner-based agent that researches a query across multiple parallel workers,
evaluates completeness with an LLM, and loops until satisfied.

Architecture:
  1. Planner     — LLM breaks the query into 4 subtopics
  2. Researchers — N parallel workers, one per subtopic
  3. Evaluator   — LLM decides SYNTHESIZE or DEEPEN (the agentic step)
       If DEEPEN → spawn new researchers for gap topics, loop
       If SYNTHESIZE → proceed to step 4
  4. Synthesizer — LLM merges all results into a final report

Data flow:
  - Small JSON (plan, eval decision) → stored directly in TitanStore
  - Large files (result txt, report md) → published to master via publish_artifact();
    orchestrator downloads with get_artifact()

Usage:
  python research_agent.py
  python research_agent.py "What are the tradeoffs of vector databases for production RAG?"

Requires:
  pip install google-genai python-dotenv
  GEMINI_API_KEY in .env or exported in shell
"""

import os
import sys
import uuid
import time
import json

from dotenv import load_dotenv
load_dotenv()

# ── Locate perm_files ──────────────────────────────────────────────────────────
_HERE       = os.path.dirname(os.path.abspath(__file__))
_ROOT       = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
_PERM_FILES = os.path.join(_ROOT, "perm_files")

_PLANNER     = os.path.join(_PERM_FILES, "research_planner.py")
_WORKER      = os.path.join(_PERM_FILES, "research_worker.py")
_EVALUATOR   = os.path.join(_PERM_FILES, "research_evaluator.py")
_SYNTHESIZER = os.path.join(_PERM_FILES, "research_synthesizer.py")

for _path in [_PLANNER, _WORKER, _EVALUATOR, _SYNTHESIZER]:
    if not os.path.exists(_path):
        print(f"[ERROR] Worker script not found: {_path}")
        sys.exit(1)

sys.path.insert(0, _ROOT)
from titan_sdk import TitanClient, TitanJob

DEFAULT_QUERY  = "What are the tradeoffs of vector databases for production RAG systems?"
MAX_ITERATIONS = 3
POLL_INTERVAL  = 2
POLL_TIMEOUT   = 300


# ── TitanStore polling helpers ─────────────────────────────────────────────────

def wait_for_signal(client: TitanClient, key: str, label: str = "",
                    timeout: int = POLL_TIMEOUT) -> bool:
    deadline = time.time() + timeout
    tag = label or key
    while time.time() < deadline:
        val = client.store_get(key)
        if val and val not in ("NULL", "CLEARED"):
            print(f"[AGENT]   {tag} — done", flush=True)
            return True
        time.sleep(POLL_INTERVAL)
    print(f"[AGENT]   {tag} — TIMED OUT after {timeout}s", flush=True)
    return False


def wait_for_signals(client: TitanClient, keys: list, labels: list = None,
                     timeout: int = POLL_TIMEOUT) -> bool:
    deadline = time.time() + timeout
    pending  = set(range(len(keys)))
    while time.time() < deadline and pending:
        for i in list(pending):
            val = client.store_get(keys[i])
            if val and val not in ("NULL", "CLEARED"):
                tag = labels[i] if labels else keys[i]
                print(f"[AGENT]   {tag} — done", flush=True)
                pending.discard(i)
        if pending:
            time.sleep(POLL_INTERVAL)
    if pending:
        still = [labels[i] if labels else keys[i] for i in pending]
        print(f"[AGENT]   TIMED OUT waiting for: {still}", flush=True)
        return False
    return True


# ── Main agent loop ────────────────────────────────────────────────────────────

def run_agent(query: str, max_iterations: int = MAX_ITERATIONS):
    run_id = uuid.uuid4().hex[:12]
    client = TitanClient()
    tag    = run_id[:6]

    print()
    print("=" * 60)
    print("  TITAN — Research Agent (Agentic Loop)")
    print("=" * 60)
    print(f"  Run ID    : {run_id}")
    print(f"  Query     : {query}")
    print(f"  Max iters : {max_iterations}")
    print("=" * 60)
    print()

    # ── Stage 1: Planner ──────────────────────────────────────────────────────
    print("[AGENT] Stage 1 — Planner: breaking query into subtopics...", flush=True)

    planner_job = TitanJob(
        job_id      = f"research-planner-{tag}",
        filename    = _PLANNER,
        args        = f"{run_id} {query.replace(' ', '_')}",
        requirement = "GENERAL",
        priority    = 5,
    )
    client.submit_dag(f"RESEARCH_{tag}_PLAN", [planner_job], agent_run_id=run_id)

    if not wait_for_signal(client, f"research:{run_id}:planner:done", label="planner", timeout=120):
        print("[ERROR] Planner timed out.", flush=True)
        sys.exit(1)

    # Read plan JSON directly from TitanStore — no filesystem access needed
    plan_json = client.store_get(f"research:{run_id}:plan")
    plan      = json.loads(plan_json)
    subtopics = plan["subtopics"]

    print(f"[AGENT] Planner decided {len(subtopics)} subtopics:", flush=True)
    for i, s in enumerate(subtopics):
        print(f"  [{i}] {s}", flush=True)

    # ── Stage 2-3: Research → Evaluate loop ───────────────────────────────────
    iteration = 0
    while iteration < max_iterations:
        iteration += 1
        print(f"\n[AGENT] Iteration {iteration}/{max_iterations} — {len(subtopics)} subtopic(s)", flush=True)

        researcher_jobs = [
            TitanJob(
                job_id      = f"research-worker-{tag}-{iteration}-{i}",
                filename    = _WORKER,
                args        = f"{run_id} {iteration} {i} {subtopics[i].replace(' ', '_')}",
                requirement = "GENERAL",
                priority    = 5,
            )
            for i in range(len(subtopics))
        ]
        print(f"[AGENT]   Submitted {len(researcher_jobs)} researcher(s) in parallel...", flush=True)
        client.submit_dag(f"RESEARCH_{tag}_ITER{iteration}", researcher_jobs, agent_run_id=run_id)

        researcher_keys   = [f"research:{run_id}:researcher:{iteration}:{i}:done" for i in range(len(subtopics))]
        researcher_labels = [f"researcher-{iteration}-{i}" for i in range(len(subtopics))]
        if not wait_for_signals(client, researcher_keys, labels=researcher_labels, timeout=180):
            print("[WARN] Some researchers timed out — proceeding to evaluation.", flush=True)

        # ── Evaluator ─────────────────────────────────────────────────────────
        evaluator_job = TitanJob(
            job_id      = f"research-evaluator-{tag}-{iteration}",
            filename    = _EVALUATOR,
            args        = f"{run_id} {iteration} {query.replace(' ', '_')}",
            requirement = "GENERAL",
            priority    = 6,
        )
        client.submit_dag(f"RESEARCH_{tag}_EVAL{iteration}", [evaluator_job], agent_run_id=run_id)

        if not wait_for_signal(client, f"research:{run_id}:eval:{iteration}:done",
                               label=f"evaluator-{iteration}", timeout=120):
            print("[WARN] Evaluator timed out — proceeding to synthesis.", flush=True)
            break

        # Read eval decision directly from TitanStore — no filesystem access needed
        eval_json = client.store_get(f"research:{run_id}:eval:{iteration}")
        decision  = json.loads(eval_json)

        if decision["decision"] == "SYNTHESIZE":
            print(f"[AGENT]   Evaluator: research complete — proceeding to synthesis.", flush=True)
            break
        else:
            gaps = decision.get("gaps", [])
            print(f"[AGENT]   Evaluator: DEEPEN — gaps: {gaps}", flush=True)
            subtopics = gaps   # LLM drives the next iteration

    # ── Stage 4: Synthesizer ──────────────────────────────────────────────────
    print(f"\n[AGENT] Stage 4 — Synthesizer: merging all research sections...", flush=True)

    synthesizer_job = TitanJob(
        job_id      = f"research-synthesizer-{tag}",
        filename    = _SYNTHESIZER,
        args        = f"{run_id} {query.replace(' ', '_')}",
        requirement = "GENERAL",
        priority    = 7,
    )
    client.submit_dag(f"RESEARCH_{tag}_SYNTH", [synthesizer_job], agent_run_id=run_id)

    if not wait_for_signal(client, f"research:{run_id}:synth:done",
                           label="synthesizer", timeout=180):
        print("[ERROR] Synthesizer timed out.", flush=True)
        sys.exit(1)

    # Download report published by synthesizer
    local_report = f"/tmp/research_{run_id}_report.md"
    client.get_artifact(f"research:{run_id}:report", save_path=local_report)

    print(f"\n[AGENT] Done. Report downloaded → {local_report}")

    print(f"\n{'=' * 60}")
    print("  REPORT PREVIEW")
    print("=" * 60)
    with open(local_report) as f:
        lines = f.readlines()
    for line in lines[:40]:
        print(line, end="")
    if len(lines) > 40:
        print(f"\n... ({len(lines) - 40} more lines — full report at {local_report})")
    print("=" * 60)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args  = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = sys.argv[1:]

    max_iter = MAX_ITERATIONS
    for i, f in enumerate(flags):
        if f == "--max-iter" and i + 1 < len(flags):
            try:
                max_iter = int(flags[i + 1])
            except ValueError:
                pass

    query = args[0] if args else DEFAULT_QUERY
    run_agent(query, max_iterations=max_iter)
