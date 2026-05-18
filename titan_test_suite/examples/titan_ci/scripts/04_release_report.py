"""
04_release_report.py — CI Step 4: Generate release report.

Runs after human approves the HITL gate. Reads all CI results from
TitanStore, writes a release_report.txt, and uploads it to the Master
so it appears in Dashboard > Workspace Files.

Args: <run_id>
"""
import sys
import json
from datetime import datetime
from titan_sdk import TitanClient

run_id = sys.argv[1]
store  = TitanClient()

print("=" * 55, flush=True)
print("[REPORT] Generating release report", flush=True)
print("=" * 55, flush=True)

def load(key):
    raw = store.store_get(key)
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}

build      = load(f"ci_{run_id}_build")
unit_tests = load(f"ci_{run_id}_unit_tests")
mock_tests = load(f"ci_{run_id}_mock_tests")
package    = load(f"ci_{run_id}_package")

now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

total_passed = unit_tests.get("passed", 0) + mock_tests.get("passed", 0)
total_failed = unit_tests.get("failed", 0) + mock_tests.get("failed", 0)
overall      = "PASSED" if total_failed == 0 else "FAILED"

lines = [
    "=" * 55,
    "  TITAN CI RELEASE REPORT",
    "=" * 55,
    f"  Run ID    : {run_id}",
    f"  Generated : {now}",
    f"  Overall   : {overall}",
    "",
    "  Build",
    f"    Status  : {build.get('status', 'N/A')}",
    f"    JAR     : {build.get('jar_kb', '?')} KB",
    f"    Time    : {build.get('elapsed', '?')}s",
    "",
    "  Unit Tests",
    f"    Status  : {unit_tests.get('status', 'N/A')}",
    f"    Passed  : {unit_tests.get('passed', 0)}",
    f"    Failed  : {unit_tests.get('failed', 0)}",
    f"    Time    : {unit_tests.get('elapsed', '?')}s",
    "",
    "  Mock Tests",
    f"    Status  : {mock_tests.get('status', 'N/A')}",
    f"    Passed  : {mock_tests.get('passed', 0)}",
    f"    Failed  : {mock_tests.get('failed', 0)}",
    f"    Time    : {mock_tests.get('elapsed', '?')}s",
    "",
    "  Bundles",
    f"    Status          : {package.get('status', 'N/A')}",
    f"    master-bundle   : {package.get('master_kb', '?')} KB",
    f"    worker-bundle   : {package.get('worker_kb', '?')} KB",
    f"    Time            : {package.get('elapsed', '?')}s",
    "",
    f"  Total tests : {total_passed + total_failed}  "
    f"passed: {total_passed}  failed: {total_failed}",
    "=" * 55,
]

report_text = "\n".join(lines)

with open("release_report.txt", "w") as f:
    f.write(report_text)

for line in lines:
    print(f"[REPORT] {line}", flush=True)

result = store.upload_file("release_report.txt")
print(f"[REPORT] Uploaded release_report.txt → {result}", flush=True)
print("[REPORT] Done.", flush=True)
