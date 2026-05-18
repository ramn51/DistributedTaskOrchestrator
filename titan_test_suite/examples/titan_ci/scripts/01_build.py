"""
01_build.py — CI Step 1: Build the Titan engine JAR.

Runs mvn clean package -DskipTests and reports the output JAR size.
Pushes build metadata to TitanStore for the report step to consume.

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
print("[BUILD] Titan Engine Build", flush=True)
print(f"[BUILD] Project root : {project_root}", flush=True)
print("=" * 55, flush=True)

start = time.time()

result = subprocess.run(
    ["mvn", "clean", "package", "-DskipTests"],
    cwd=project_root,
    capture_output=True,
    text=True,
)

elapsed = round(time.time() - start, 1)

if result.returncode != 0:
    print("[BUILD] FAILED", flush=True)
    print(result.stdout[-3000:], flush=True)
    print(result.stderr[-2000:], flush=True)
    store.store_put(f"ci_{run_id}_build", json.dumps({"status": "FAILED", "elapsed": elapsed}))
    sys.exit(1)

jar = os.path.join(project_root, "target", "titan-orchestrator-1.0-SNAPSHOT.jar")
jar_kb = os.path.getsize(jar) // 1024 if os.path.exists(jar) else 0

print(f"[BUILD] SUCCESS in {elapsed}s", flush=True)
print(f"[BUILD] JAR size : {jar_kb} KB", flush=True)

store.store_put(f"ci_{run_id}_build", json.dumps({
    "status":  "PASSED",
    "elapsed": elapsed,
    "jar_kb":  jar_kb,
}))

print("[BUILD] Done.", flush=True)
