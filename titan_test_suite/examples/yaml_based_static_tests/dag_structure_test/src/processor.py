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

import sys
import time
import os

mode = sys.argv[1] if len(sys.argv) > 1 else "UNKNOWN"
print(f"[{mode}] Running on Worker...")
print(f"[{mode}] Current Directory: {os.getcwd()}")

# Simulate work
time.sleep(1)
print(f"[{mode}] Complete.")