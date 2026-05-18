# Titan CI Pipeline (Dogfooding)

!!! abstract "Dogfooding"
    Titan runs its own build, test, and release pipeline using itself. This is the most honest demonstration of what Titan does well — not a contrived example, but a workflow that actually runs in this project.

---

## What It Does

```
build (mvn package)
 ├── unit-tests    ←─ parallel
 └── mock-tests    ←─ parallel
      ↓ fan-in (both must pass)
 package-bundles
      ↓
 [HITL gate] "Tests passed. Approve release?"
      ↓ you approve in the Dashboard
 release-report   ← collects all results, uploads summary
```

- **Build and tests run in parallel** — unit and mock tests both start the moment the build finishes, on separate workers simultaneously
- **Fan-in before packaging** — bundles are only built if both test suites pass
- **HITL gate** — pipeline pauses and waits for a human to approve in the Dashboard before generating the release report. This is where Titan wins over a bash script — a clean, auditable human checkpoint mid-pipeline
- **TitanStore as the data bus** — each step writes its results (pass count, elapsed time, JAR size) to TitanStore; the report step reads them all and assembles the summary

---

## Why Not a Bash Script?

A bash script can run tests and check exit codes. What it can't do cleanly:

- **Pause mid-pipeline for human approval** and resume only after a decision in a UI
- **Show per-job logs individually** — in bash, all output mixes in one terminal; here each job has its own log stream in the Visualizer
- **Replay a single failed step** — if mock tests fail, you can fix the issue and replay just that job from the Dashboard without re-running the build
- **Fan-in semantics** — packaging waits for both test jobs to complete; bash needs explicit `wait` + exit code bookkeeping

---

## Running It

Make sure your local Titan cluster is up:

```bash
./titan-dev.sh up
```

Then:

```bash
python titan_test_suite/examples/titan_ci/titan_ci.py
```

Open the Dashboard at `http://localhost:5000`. You will see the pipeline `TITAN_CI_<run_id>` with the DAG graph:

```
build ──► unit-tests ──► package ──► [HITL] ──► release-report
      └──► mock-tests ──┘
```

When `package` completes, the HITL gate activates. A prompt appears in the Dashboard — click **Approve** to continue to the release report, or **Reject** to abort.

---

## Output

After approval, `release-report.txt` is generated and uploaded to the Master. Download it from **Dashboard → Visualizer → `ci-<run_id>-report` → Workspace Files**.

Example report:
```
=======================================================
  TITAN CI RELEASE REPORT
=======================================================
  Run ID    : a3f1bc09
  Generated : 2026-05-17 14:32 UTC
  Overall   : PASSED

  Build
    Status  : PASSED
    JAR     : 8821 KB
    Time    : 34.2s

  Unit Tests
    Status  : PASSED
    Passed  : 12
    Failed  : 0
    Time    : 1.8s

  Mock Tests
    Status  : PASSED
    Passed  : 4
    Failed  : 0
    Time    : 0.9s

  Bundles
    Status        : PASSED
    master-bundle : 2304 KB
    worker-bundle : 120 KB
    Time          : 18.1s

  Total tests : 16  passed: 16  failed: 0
=======================================================
```

---

## File Reference

```
titan_test_suite/examples/titan_ci/
├── titan_ci.py                  ← orchestrator — run this
└── scripts/
    ├── 01_build.py              ← mvn clean package
    ├── 02_unit_tests.py         ← pytest titan_sdk/tests/unit/
    ├── 02_mock_tests.py         ← pytest titan_sdk/tests/mock/  (parallel with above)
    ├── 03_package.py            ← package_cloud.sh (fan-in from both test jobs)
    └── 04_release_report.py     ← reads TitanStore, writes + uploads report
```
