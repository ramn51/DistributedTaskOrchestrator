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
import datetime

def log(msg):
    # Print with timestamp to see exactly when execution halts/resumes
    timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {msg}", flush=True)

log("--- [START] Debug Computation Task ---")

total_sum = 0
steps = 20
delay = 0.5 # 500ms delay

for i in range(1, steps + 1):
    time.sleep(delay)
    total_sum += i

    # Log every 5 steps to keep output readable but frequent enough to see stalls
    if i % 5 == 0 or i == 1:
        log(f"Processing Step {i}/{steps}... (Sum: {total_sum})")

log(f"--- [DONE] Final Result: {total_sum} ---")