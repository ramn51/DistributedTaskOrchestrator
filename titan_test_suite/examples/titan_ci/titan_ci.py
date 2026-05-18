"""
titan_ci.py — Titan CI pipeline (dogfooding).

Uses Titan to run Titan's own build, test, and release pipeline.

DAG structure:
    build
     ├── unit-tests   ← parallel fan-out (no cluster needed)
     └── mock-tests   ← parallel fan-out (no cluster needed)
          ↓ fan-in (both must pass before packaging)
     package-bundles
          ↓
     [HITL gate] "Tests passed. Approve release?"
          ↓ human approves in Dashboard
     release-report   ← collects results, uploads summary

Usage:
    python titan_test_suite/examples/titan_ci/titan_ci.py
"""
import os
import uuid
from titan_sdk import TitanClient, TitanJob

def script(name):
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts")
    return os.path.join(base, name)

def run():
    run_id       = uuid.uuid4().hex[:8]
    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..")
    )
    client = TitanClient()

    print("=" * 55)
    print("  Titan CI Pipeline")
    print("=" * 55)
    print(f"  Run ID       : {run_id}")
    print(f"  Project root : {project_root}")
    print("=" * 55)

    # ── Step 1: Build ────────────────────────────────────────
    job_build = TitanJob(
        job_id      = f"ci-{run_id}-build",
        filename    = script("01_build.py"),
        args        = f"{project_root} {run_id}",
        requirement = "GENERAL",
        priority    = 10,
    )

    # ── Step 2: Tests (parallel fan-out from build) ──────────
    job_unit_tests = TitanJob(
        job_id      = f"ci-{run_id}-unit-tests",
        filename    = script("02_unit_tests.py"),
        args        = f"{project_root} {run_id}",
        parents     = [job_build.id],
        requirement = "GENERAL",
        priority    = 10,
    )

    job_mock_tests = TitanJob(
        job_id      = f"ci-{run_id}-mock-tests",
        filename    = script("02_mock_tests.py"),
        args        = f"{project_root} {run_id}",
        parents     = [job_build.id],
        requirement = "GENERAL",
        priority    = 10,
    )

    # ── Step 3: Package (fan-in — both tests must pass) ──────
    job_package = TitanJob(
        job_id      = f"ci-{run_id}-package",
        filename    = script("03_package.py"),
        args        = f"{project_root} {run_id}",
        parents     = [job_unit_tests.id, job_mock_tests.id],
        requirement = "GENERAL",
        priority    = 10,
        hitl_message = (
            f"CI run {run_id}: build passed, all tests green, bundles ready. "
            f"Approve to generate release report."
        ),
    )

    # ── Step 4: Release report (after HITL approval) ─────────
    job_report = TitanJob(
        job_id      = f"ci-{run_id}-report",
        filename    = script("04_release_report.py"),
        args        = run_id,
        parents     = [job_package.id],
        requirement = "GENERAL",
        priority    = 10,
    )

    # ── Submit ────────────────────────────────────────────────
    dag_name = f"TITAN_CI_{run_id}"
    client.submit_dag(dag_name, [
        job_build,
        job_unit_tests,
        job_mock_tests,
        job_package,
        job_report,
    ])

    print()
    print(f"[CI] DAG submitted: {dag_name}")
    print()
    print("  Watch it run:")
    print("  → Dashboard : http://localhost:5000")
    print()
    print("  You will be prompted to approve in the Dashboard")
    print("  once the build and tests complete.")

if __name__ == "__main__":
    run()
