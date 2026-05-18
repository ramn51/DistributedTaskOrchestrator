"""
cpu_prepare.py — Runs on a GENERAL worker.

Simulates data preparation: generates a dataset, computes stats,
and pushes the result to TitanStore for the downstream GPU job to consume.
"""
import time
import random
import json
import sys
from titan_sdk import TitanClient

RUN_ID = sys.argv[1] if len(sys.argv) > 1 else "default"

print("=" * 50, flush=True)
print(f"[CPU] Data Preparation Job", flush=True)
print(f"[CPU] Run ID : {RUN_ID}", flush=True)
print("=" * 50, flush=True)

print("[CPU] Generating synthetic dataset...", flush=True)
time.sleep(3)

random.seed(42)
num_samples = 1000
dataset = {
    "run_id":      RUN_ID,
    "num_samples": num_samples,
    "features":    4,
    "classes":     ["cat", "dog", "bird"],
    "class_dist":  {"cat": 320, "dog": 318, "bird": 362},
    "mean":        round(random.uniform(0.45, 0.55), 4),
    "std":         round(random.uniform(0.18, 0.25), 4),
    "null_count":  random.randint(0, 20),
    "status":      "READY",
}

print(f"[CPU] Dataset summary:", flush=True)
print(f"[CPU]   Samples  : {dataset['num_samples']}", flush=True)
print(f"[CPU]   Features : {dataset['features']}", flush=True)
print(f"[CPU]   Classes  : {dataset['classes']}", flush=True)
print(f"[CPU]   Nulls    : {dataset['null_count']}", flush=True)
print(f"[CPU]   Mean     : {dataset['mean']}", flush=True)
print(f"[CPU]   Std      : {dataset['std']}", flush=True)

# Push to TitanStore — GPU job will read this
client = TitanClient()
key = f"gpu_pipeline_{RUN_ID}_dataset"
resp = client.store_put(key, json.dumps(dataset))

if resp == "OK":
    print(f"[CPU] Dataset pushed to TitanStore → key: {key}", flush=True)
else:
    print(f"[CPU] ERROR: TitanStore write failed: {resp}", flush=True)
    sys.exit(1)

print("[CPU] Data preparation complete. GPU job can now proceed.", flush=True)
print("=" * 50, flush=True)
