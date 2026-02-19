#  Copyright 2026 Ram Narayanan
#  Licensed under the Apache License, Version 2.0

import time
import sys
from titan_sdk import TitanClient

# Args passed from job: "worker_1", "worker_2", etc.
my_id = "unknown"
if len(sys.argv) > 1:
    my_id = sys.argv[1]

print(f"[{my_id}] Starting work...")
time.sleep(1)

client = TitanClient()
print(f"[{my_id}] Registering presence in 'titan_active_workers'...")

# Add ID to the Set
# Note: Ensure your SDK has store_sadd implemented!
count = client.store_sadd("titan_active_workers", my_id)

print(f"[{my_id}] Registration complete. (New? {count})")