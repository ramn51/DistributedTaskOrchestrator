"""
02_mock_tests.py — CI Step 2b: Run SDK mock tests.

Runs pytest on titan_sdk/tests/mock/ — no running cluster required.
Runs in parallel with 02_unit_tests.py (same parent: build job).
Pushes pass/fail counts to TitanStore for the report step.

Args: <project_root> <run_id>
"""
import subprocess
import sys
import json
import re
import time
from titan_sdk import TitanClient

project_root = sys.argv[1]
run_id       = sys.argv[2]
store        = TitanClient()

test_path = f"{project_root}/titan_sdk/tests/mock"

print("=" * 55, flush=True)
print("[MOCK-TESTS] SDK Mock Tests", flush=True)
print(f"[MOCK-TESTS] Path : {test_path}", flush=True)
print("=" * 55, flush=True)

start = time.time()

result = subprocess.run(
    ["python", "-m", "pytest", test_path, "-v", "--tb=short"],
    cwd=project_root,
    capture_output=True,
    text=True,
)

elapsed = round(time.time() - start, 1)

for line in result.stdout.split("\n"):
    print(f"[MOCK-TESTS] {line}", flush=True)
if result.stderr:
    for line in result.stderr.split("\n"):
        print(f"[MOCK-TESTS] {line}", flush=True)

summary = ""
passed = failed = 0
for line in result.stdout.split("\n"):
    if re.search(r"\d+ passed", line) or re.search(r"\d+ failed", line):
        summary = line.strip()
        m = re.search(r"(\d+) passed", line)
        if m: passed = int(m.group(1))
        m = re.search(r"(\d+) failed", line)
        if m: failed = int(m.group(1))

status = "PASSED" if result.returncode == 0 else "FAILED"
print(f"[MOCK-TESTS] {status} — {summary} ({elapsed}s)", flush=True)

store.store_put(f"ci_{run_id}_mock_tests", json.dumps({
    "status":  status,
    "passed":  passed,
    "failed":  failed,
    "elapsed": elapsed,
    "summary": summary,
}))

if result.returncode != 0:
    sys.exit(result.returncode)

print("[MOCK-TESTS] Done.", flush=True)
