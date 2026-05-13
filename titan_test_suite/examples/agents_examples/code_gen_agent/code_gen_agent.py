#  Copyright 2026 Ram Narayanan
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0

"""
Code Generation Agent — Titan Agentic Example
==============================================

A planner-based agent that generates, reviews, and fixes code across
multiple parallel workers — with a different loop condition and extra
integration stage compared to the Research Agent.

Architecture:
  1. Planner     — LLM decomposes the goal into independent components
  2. Generators  — N parallel workers, one per component, write code
  3. Reviewer    — LLM reviews ALL components: APPROVE or REQUEST_CHANGES
       If REQUEST_CHANGES → spawn targeted fix workers (only flagged components)
       Loop back to reviewer
       If APPROVE → proceed to step 4
  4. Integrator  — LLM merges all approved components into one final file

Data flow:
  - Small JSON (plan, review decision) → stored directly in TitanStore
  - Component code → stored directly in TitanStore (key: code:{run_id}:component:{idx}:content)
  - Final integrated file → published to master via publish_artifact();
    orchestrator downloads with get_artifact()

Usage:
  python code_gen_agent.py
  python code_gen_agent.py "Build a Python CLI task manager with priority queuing and JSON persistence"

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
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))

# Worker scripts live alongside this orchestrator
_PLANNER    = os.path.join(_HERE, "code_planner.py")
_GENERATOR  = os.path.join(_HERE, "code_generator.py")
_REVIEWER   = os.path.join(_HERE, "code_reviewer.py")
_FIXER      = os.path.join(_HERE, "code_fixer.py")
_INTEGRATOR = os.path.join(_HERE, "code_integrator.py")

for _path in [_PLANNER, _GENERATOR, _REVIEWER, _FIXER, _INTEGRATOR]:
    if not os.path.exists(_path):
        print(f"[ERROR] Worker script not found: {_path}")
        sys.exit(1)

sys.path.insert(0, _ROOT)
from titan_sdk import TitanClient, TitanJob

DEFAULT_GOAL   = "Build a Python CLI task manager with priority queuing and JSON persistence"
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

def run_agent(goal: str, max_iterations: int = MAX_ITERATIONS):
    run_id = uuid.uuid4().hex[:12]
    client = TitanClient()
    tag    = run_id[:6]

    print()
    print("=" * 60)
    print("  TITAN — Code Generation Agent (Agentic Loop)")
    print("=" * 60)
    print(f"  Run ID    : {run_id}")
    print(f"  Goal      : {goal}")
    print(f"  Max iters : {max_iterations}")
    print("=" * 60)
    print()

    # ── Stage 1: Planner ──────────────────────────────────────────────────────
    # ── Stage 1: Planner ──────────────────────────────────────────────────────
    print("[AGENT] Stage 1 — Planner: decomposing goal into components...", flush=True)

    planner_job = TitanJob(
        job_id      = f"code-planner-{tag}",
        filename    = _PLANNER,
        args        = f"{run_id} {goal.replace(' ', '_')}",
        requirement = "GENERAL",
        priority    = 5,
    )
    client.submit_dag(f"CODE_{tag}_PLAN", [planner_job], agent_run_id=run_id)

    if not wait_for_signal(client, f"code:{run_id}:planner:done", label="planner", timeout=120):
        print("[ERROR] Planner timed out.", flush=True)
        sys.exit(1)

    # Read plan JSON directly from TitanStore — no filesystem access needed
    plan_json  = client.store_get(f"code:{run_id}:plan")
    plan       = json.loads(plan_json)
    components = sorted(plan["components"], key=lambda c: c["idx"])

    print(f"[AGENT] Planner decomposed into {len(components)} components:", flush=True)
    for c in components:
        print(f"  [{c['idx']}] {c['name']} — {c['description'][:65]}...", flush=True)

    # ── Stage 2: Generate all components in parallel ──────────────────────────
    print(f"\n[AGENT] Stage 2 — Generating {len(components)} components in parallel...", flush=True)

    generator_jobs = [
        TitanJob(
            job_id      = f"code-gen-{tag}-{c['idx']}",
            filename    = _GENERATOR,
            args        = f"{run_id} 1 {c['idx']}",
            requirement = "GENERAL",
            priority    = 5,
        )
        for c in components
    ]
    client.submit_dag(f"CODE_{tag}_GEN1", generator_jobs, agent_run_id=run_id)

    gen_keys   = [f"code:{run_id}:generator:1:{c['idx']}:done" for c in components]
    gen_labels = [f"generator-{c['name']}" for c in components]
    if not wait_for_signals(client, gen_keys, labels=gen_labels, timeout=180):
        print("[WARN] Some generators timed out — proceeding with available code.", flush=True)

    # ── Stage 3: Review → Fix loop ────────────────────────────────────────────
    iteration = 0
    while iteration < max_iterations:
        iteration += 1
        print(f"\n[AGENT] Stage 3 — Reviewer (iteration {iteration}/{max_iterations})...", flush=True)

        reviewer_job = TitanJob(
            job_id      = f"code-reviewer-{tag}-{iteration}",
            filename    = _REVIEWER,
            args        = f"{run_id} {iteration} {goal.replace(' ', '_')}",
            requirement = "GENERAL",
            priority    = 6,
        )
        client.submit_dag(f"CODE_{tag}_REVIEW{iteration}", [reviewer_job], agent_run_id=run_id)

        if not wait_for_signal(client, f"code:{run_id}:reviewer:{iteration}:done",
                               label=f"reviewer-{iteration}", timeout=120):
            print("[WARN] Reviewer timed out — proceeding to integration.", flush=True)
            break

        # Read review decision directly from TitanStore — no filesystem access needed
        review_json = client.store_get(f"code:{run_id}:review:{iteration}")
        review      = json.loads(review_json)

        if review["decision"] == "APPROVE":
            print(f"[AGENT]   Reviewer: code approved — proceeding to integration.", flush=True)
            break

        # REQUEST_CHANGES — spawn targeted fixers only for flagged components
        issues = review.get("issues", [])
        print(f"[AGENT]   Reviewer: {len(issues)} issue(s) found — spawning targeted fixers:", flush=True)
        for i, issue in enumerate(issues):
            print(f"    [{i}] {issue['component_name']}: {issue['problem'][:70]}", flush=True)

        fixer_jobs = [
            TitanJob(
                job_id      = f"code-fixer-{tag}-{iteration}-{i}",
                filename    = _FIXER,
                args        = f"{run_id} {iteration} {i}",
                requirement = "GENERAL",
                priority    = 7,
            )
            for i in range(len(issues))
        ]
        client.submit_dag(f"CODE_{tag}_FIX{iteration}", fixer_jobs, agent_run_id=run_id)

        fix_keys   = [f"code:{run_id}:fixer:{iteration}:{i}:done" for i in range(len(issues))]
        fix_labels = [f"fixer-{issues[i]['component_name']}" for i in range(len(issues))]
        if not wait_for_signals(client, fix_keys, labels=fix_labels, timeout=180):
            print("[WARN] Some fixers timed out — proceeding with available fixes.", flush=True)

    if iteration >= max_iterations:
        print(f"\n[AGENT] Max review iterations reached — integrating best available code.", flush=True)

    # ── Stage 4: Integrator ───────────────────────────────────────────────────
    print(f"\n[AGENT] Stage 4 — Integrator: merging {len(components)} approved component(s)...", flush=True)

    integrator_job = TitanJob(
        job_id      = f"code-integrator-{tag}",
        filename    = _INTEGRATOR,
        args        = f"{run_id} {goal.replace(' ', '_')}",
        requirement = "GENERAL",
        priority    = 8,
    )
    client.submit_dag(f"CODE_{tag}_INTEGRATE", [integrator_job], agent_run_id=run_id)

    if not wait_for_signal(client, f"code:{run_id}:integrator:done", label="integrator", timeout=120):
        print("[ERROR] Integrator timed out.", flush=True)
        sys.exit(1)

    # Download final file published by integrator
    local_final = f"/tmp/code_{run_id}_final.py"
    client.get_artifact(f"code:{run_id}:final", save_path=local_final)

    print(f"\n[AGENT] Done.")
    print(f"[AGENT] Final code downloaded → {local_final}")

    print(f"\n{'=' * 60}")
    print("  GENERATED CODE PREVIEW")
    print("=" * 60)
    with open(local_final) as f:
        lines = f.readlines()
    for line in lines[:50]:
        print(line, end="")
    if len(lines) > 50:
        print(f"\n... ({len(lines) - 50} more lines — full file at {local_final})")
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

    goal = args[0] if args else DEFAULT_GOAL
    run_agent(goal, max_iterations=max_iter)
