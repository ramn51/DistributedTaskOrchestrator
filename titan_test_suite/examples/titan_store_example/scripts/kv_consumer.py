#  Copyright 2026 Ram Narayanan
#  Licensed under the Apache License, Version 2.0

import time
import sys
from titan_sdk import TitanClient

print("[CONSUMER] Connecting to Distributed Store...")
client = TitanClient()

# Read from Master's Redis
val = client.store_get("titan_secret_code")

print(f"[CONSUMER] Retrieved Value: {val}")

if val == "SECRET_123":
    print("[CONSUMER] VALIDATION SUCCESS: Data match.")
else:
    print(f"[CONSUMER] VALIDATION FAIL: Expected 'SECRET_123', got '{val}'")
    sys.exit(1)