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

print("[FAST-SCAN] Initializing quick diagnostic scan...")
time.sleep(1) # Simulate work

print("[FAST-SCAN] Checking critical metrics only...")
# Simulate a quick check
metrics = {"cpu": "OK", "memory": "OK", "disk": "OK"}
print(f"[FAST-SCAN] Results: {metrics}")

print("[FAST-SCAN] Scan complete. System healthy.")