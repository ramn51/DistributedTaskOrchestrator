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

import time
import sys
import random

# Simulate processing a specific chunk
worker_id = random.randint(1000, 9999)
print(f"[WORKER-{worker_id}] Received data chunk.")

process_time = 3
print(f"[WORKER-{worker_id}] Crunching numbers (Duration: {process_time}s)...")
time.sleep(process_time)

print(f"[WORKER-{worker_id}] Analysis complete. Confidence Score: 98%.")