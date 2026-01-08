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

def long_calculation_new_calc():
    print("[Calc] Starting complex calculation job...", flush=True)

    # Simulate initialization (2 seconds)
    time.sleep(2)
    print("[Calc] Step 1: Loading data...", flush=True)

    # Simulate processing (2 seconds)
    time.sleep(2)
    print("[Calc] Step 2: Crunching numbers...", flush=True)

    # Simulate finalization (2 seconds)
    time.sleep(2)
    print("[Calc] Step 3: Verifying results...", flush=True)

    # Actual calculation
    total = sum(range(101))

    # Final Result
    print(f"Result: {total}", flush=True)

if __name__ == "__main__":
    long_calculation_new_calc()