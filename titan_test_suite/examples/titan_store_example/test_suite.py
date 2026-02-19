#  Copyright 2026 Ram Narayanan
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND.

import time, os, sys
from titan_sdk import TitanClient, TitanJob

# CONFIGURATION
TITAN_PORT = 10000  # Ensure this matches your running Master

def get_script_path(script_name):
    # Assumes scripts are in a 'scripts' subdirectory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(current_dir, "scripts", script_name)
    if not os.path.exists(path):
        # Fallback: create the directory if missing
        os.makedirs(os.path.join(current_dir, "scripts"), exist_ok=True)
    return path

def run_persistence_test():
    print("🚀 STARTING TITAN PERSISTENCE SUITE 🚀")
    client = TitanClient()

    # --- SCENARIO 1: The Baton Pass (KV Store) ---
    # Job A generates a 'Secret Code' and puts it in Redis.
    # Job B reads that code. If it fails to read, the test fails.
    
    print("\n[TEST 1] Distributed Data Passing (KV Store)...")
    
    # 1. Producer Job
    job_producer = TitanJob(
        job_id="KV_PRODUCER",
        filename=get_script_path("kv_producer.py"),
        priority=10
    )

    # 2. Consumer Job (Depends on Producer)
    job_consumer = TitanJob(
        job_id="KV_CONSUMER",
        filename=get_script_path("kv_consumer.py"),
        parents=["KV_PRODUCER"],
        priority=10
    )
    
    client.submit_dag("DATA_PIPELINE", [job_producer, job_consumer])
    print(">> Submitted Producer -> Consumer DAG.")


    # --- SCENARIO 2: The Fan-In (Sets) ---
    # We spawn 3 workers. They all register themselves in a Redis Set.
    # The Client then checks if all 3 are present.
    
    print("\n[TEST 2] Distributed Fan-In (Sets)...")
    
    fan_jobs = []
    for i in range(1, 4):
        job = TitanJob(
            job_id=f"SET_WORKER_{i}",
            filename=get_script_path("set_worker.py"),
            args=f"worker_{i}", # Pass ID as arg
            priority=5
        )
        fan_jobs.append(job)
        
    client.submit_dag("FAN_IN_CLUSTER", fan_jobs)
    print(">> Submitted 3 Set-Worker Jobs.")


    # --- VERIFICATION LOOP ---
    print("\n[MONITOR] Waiting for results in Redis...")
    
    # Check for Scenario 1 Success
    start_time = time.time()
    kv_success = False
    set_success = False
    
    while time.time() - start_time < 30: # 30s Timeout
        # 1. Check KV Result
        secret = client.store_get("titan_secret_code")
        if secret and "SECRET_123" in secret and not kv_success:
            print("✅ [PASS] KV Store: Consumer successfully processed the secret.")
            kv_success = True
            
        # 2. Check Set Result
        members = client.store_smembers("titan_active_workers")
        if len(members) >= 3 and not set_success:
            print(f"✅ [PASS] Sets: All 3 workers registered! Found: {members}")
            set_success = True
            
        if kv_success and set_success:
            print("\n🏆 ALL SYSTEM TESTS PASSED 🏆")
            return

        time.sleep(2)
        print(".", end="", flush=True)

    print("\n❌ TIMEOUT: Test incomplete.")
    if not kv_success: print("   - KV Store Test Failed (Secret not found)")
    if not set_success: print("   - Set Test Failed (Workers missing)")

if __name__ == "__main__":
    run_persistence_test()