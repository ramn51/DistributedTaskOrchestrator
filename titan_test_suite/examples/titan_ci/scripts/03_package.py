"""
03_package.py — CI Step 3: Package cloud deployment bundles.

Runs package_cloud.sh to produce titan-master-bundle.zip and
titan-worker-bundle.zip. Pushes bundle sizes to TitanStore.

Only runs after BOTH unit and mock tests pass (fan-in dependency
enforced by the DAG).

Args: <project_root> <run_id>
"""
import subprocess
import sys
import os
import json
import time
from titan_sdk import TitanClient

project_root = sys.argv[1]
run_id       = sys.argv[2]
store        = TitanClient()

print("=" * 55, flush=True)
print("[PACKAGE] Building cloud deployment bundles", flush=True)
print("=" * 55, flush=True)

start  = time.time()
script = os.path.join(project_root, "package_cloud.sh")

result = subprocess.run(
    ["bash", script],
    cwd=project_root,
    capture_output=True,
    text=True,
)

elapsed = round(time.time() - start, 1)

for line in result.stdout.split("\n"):
    print(f"[PACKAGE] {line}", flush=True)

if result.returncode != 0:
    print(f"[PACKAGE] FAILED (exit {result.returncode})", flush=True)
    store.store_put(f"ci_{run_id}_package", json.dumps({"status": "FAILED"}))
    sys.exit(result.returncode)

master_zip = os.path.join(project_root, "titan-master-bundle.zip")
worker_zip = os.path.join(project_root, "titan-worker-bundle.zip")

master_kb = os.path.getsize(master_zip) // 1024 if os.path.exists(master_zip) else 0
worker_kb = os.path.getsize(worker_zip) // 1024 if os.path.exists(worker_zip) else 0

print(f"[PACKAGE] titan-master-bundle.zip : {master_kb} KB", flush=True)
print(f"[PACKAGE] titan-worker-bundle.zip : {worker_kb} KB", flush=True)
print(f"[PACKAGE] Done in {elapsed}s", flush=True)

store.store_put(f"ci_{run_id}_package", json.dumps({
    "status":    "PASSED",
    "elapsed":   elapsed,
    "master_kb": master_kb,
    "worker_kb": worker_kb,
}))
