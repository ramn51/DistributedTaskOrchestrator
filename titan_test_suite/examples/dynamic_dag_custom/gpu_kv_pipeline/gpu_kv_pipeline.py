"""
gpu_kv_pipeline.py — CPU + GPU routing with KV passing via TitanStore.

Architecture:
    cpu_prepare  (GENERAL worker, local)
        → generates dataset, pushes summary to TitanStore
            ↓  (DAG dependency edge)
    gpu_compute  (GPU worker — RunPod / H100)
        → reads dataset stats from TitanStore (titan_sdk required on worker)
        → runs training
        → writes model_report.txt to workspace (downloadable from Dashboard)

Both jobs are submitted as a single DAG so the Visualizer shows them
as one connected pipeline.

Usage:
    python gpu_kv_pipeline.py
"""
import os
import uuid
from titan_sdk import TitanClient, TitanJob

def script(name):
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts")
    return os.path.join(base, name)

def run():
    run_id = uuid.uuid4().hex[:8]
    client = TitanClient()

    print("=" * 50)
    print("  GPU + CPU Pipeline")
    print("=" * 50)
    print(f"  Run ID : {run_id}")
    print("=" * 50)

    cpu_job = TitanJob(
        job_id      = f"cpu-prepare-{run_id}",
        filename    = script("cpu_prepare.py"),
        args        = run_id,
        requirement = "GENERAL",
        priority    = 5,
    )

    # GPU job depends on cpu_job — Titan ensures cpu_prepare completes first.
    # gpu_compute reads the dataset directly from TitanStore (titan_sdk on worker).
    gpu_job = TitanJob(
        job_id      = f"gpu-compute-{run_id}",
        filename    = script("gpu_compute.py"),
        args        = run_id,
        parents     = [cpu_job.id],
        requirement = "GPU",
        priority    = 8,
    )

    # Single DAG submission → both jobs appear as one connected pipeline in the Visualizer
    client.submit_dag(f"GPU_KV_PIPELINE_{run_id}", [cpu_job, gpu_job])

    print(f"[PIPELINE] DAG submitted — cpu-prepare → gpu-compute")
    print()
    print("  Watch it run:")
    print("  → Dashboard : http://localhost:5000")

if __name__ == "__main__":
    run()
