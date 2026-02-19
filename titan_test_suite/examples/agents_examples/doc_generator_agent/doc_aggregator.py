import os
import base64
from titan_sdk import TitanClient, TitanJob

# --- CONFIG ---
TARGET_DIRS = ["src/main/java/titan", "titan_sdk"]
CURRENT_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Adjust path to find your DistributedOrchestrator root
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_SCRIPT_DIR, "../../../.."))
WORKER_SCRIPT = os.path.join(CURRENT_SCRIPT_DIR, "tools", "printer_worker.py")

def seed_and_dispatch():
    client = TitanClient()
    batch_jobs = []

    for target_dir in TARGET_DIRS:
        scan_path = os.path.join(PROJECT_ROOT, target_dir)
        if not os.path.exists(scan_path): continue

        for root, _, files in os.walk(scan_path):
            for file in files:
                if file.endswith((".java", ".py")):
                    abs_path = os.path.join(root, file)
                    with open(abs_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 1. Store RAW text
                    raw_key = f"RAW:{file}"
                    client.store_put(raw_key, content)
                    
                    # 2. Dispatch Job
                    job_id = f"JSON_WRAP_{file.replace('.', '_')}"
                    batch_jobs.append(TitanJob(
                        job_id=job_id,
                        filename=WORKER_SCRIPT,
                        args=raw_key  # Passing the KEY as the argument
                    ))

    client.submit_dag("INITIAL_JSON_WRAP", batch_jobs)
    print(f"✅ Seeding complete. {len(batch_jobs)} jobs sent.")

if __name__ == "__main__":
    seed_and_dispatch()