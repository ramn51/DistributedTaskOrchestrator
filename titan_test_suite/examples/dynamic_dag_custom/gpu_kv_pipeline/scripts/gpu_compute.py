"""
gpu_compute.py — Runs on a GPU worker (RunPod / H100).

Reads dataset stats from TitanStore (written by the upstream cpu_prepare job),
simulates GPU training, and writes model_report.txt to the workspace
for download from the Dashboard.

Requires titan_sdk installed on the GPU worker (see docs/deployment/remote-gpu-worker.md).

Args: <run_id>
"""
import time
import random
import sys
import json
from titan_sdk import TitanClient

RUN_ID = sys.argv[1] if len(sys.argv) > 1 else "default"

# Read dataset stats that cpu_prepare pushed to TitanStore
store       = TitanClient()
dataset_key = f"gpu_pipeline_{RUN_ID}_dataset"
raw         = store.store_get(dataset_key)
try:
    dataset = json.loads(raw)
except (json.JSONDecodeError, TypeError):
    print(f"[GPU] ERROR: Could not read dataset from TitanStore key: {dataset_key}", flush=True)
    print(f"[GPU]        Raw value: {raw!r}", flush=True)
    sys.exit(1)

num_samples = dataset["num_samples"]
mean        = dataset["mean"]
std         = dataset["std"]
classes     = dataset.get("classes", [])

print("=" * 50, flush=True)
print(f"[GPU] Training Job", flush=True)
print(f"[GPU] Run ID : {RUN_ID}", flush=True)
print("=" * 50, flush=True)
print(f"[GPU] Dataset received via args:", flush=True)
print(f"[GPU]   Samples : {num_samples}", flush=True)
print(f"[GPU]   Mean    : {mean}", flush=True)
print(f"[GPU]   Std     : {std}", flush=True)

# Simulate GPU training
print(f"\n[GPU] Starting training (5 epochs)...", flush=True)
time.sleep(2)

random.seed(99)
epochs = 5
history = []
loss = 1.05
acc  = -0.02

for epoch in range(1, epochs + 1):
    time.sleep(1)
    loss = round(loss * random.uniform(0.55, 0.65), 4)
    acc  = round(min(acc + random.uniform(0.13, 0.18), 0.99), 4)
    history.append({"epoch": epoch, "loss": loss, "acc": acc})
    print(f"[GPU]   Epoch {epoch}/{epochs}  loss={loss:.4f}  acc={acc:.4f}", flush=True)

final_acc  = history[-1]["acc"]
final_loss = history[-1]["loss"]

print(f"\n[GPU] Training complete.", flush=True)
print(f"[GPU] Final accuracy : {final_acc}", flush=True)
print(f"[GPU] Final loss     : {final_loss}", flush=True)

print(f"[GPU] Final accuracy : {final_acc}", flush=True)
print(f"[GPU] Final loss     : {final_loss}", flush=True)

# Write model_report.txt to local workspace — visible in Dashboard > Workspace Files
report_lines = [
    "=" * 50,
    "  GPU TRAINING REPORT",
    "=" * 50,
    f"  Run ID       : {RUN_ID}",
    f"  Samples      : {num_samples}",
    f"  Classes      : {classes}",
    f"  Mean / Std   : {mean} / {std}",
    "",
    "  Training History:",
]
for h in history:
    report_lines.append(f"    Epoch {h['epoch']}: loss={h['loss']}  acc={h['acc']}")

report_lines += [
    "",
    f"  Final Accuracy : {final_acc}",
    f"  Final Loss     : {final_loss}",
    "=" * 50,
]

report_text = "\n".join(report_lines)

# Write to current working directory — Titan worker stages this as a workspace file
with open("model_report.txt", "w") as f:
    f.write(report_text)

print(f"[GPU] model_report.txt written to workspace.", flush=True)
print(report_text, flush=True)
print("=" * 50, flush=True)

# Upload report back to Master so it appears in Dashboard > Workspace Files
result = store.upload_file("model_report.txt")
print(f"[GPU] upload model_report.txt → {result}", flush=True)
