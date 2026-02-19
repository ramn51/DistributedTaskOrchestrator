#  Copyright 2026 Ram Narayanan
#  Licensed under the Apache License, Version 2.0

import time
import sys
from titan_sdk import TitanClient

print("[PRODUCER] Generating Data...")
time.sleep(2) # Simulate calculation

secret_code = "SECRET_123"
print(f"[PRODUCER] Generated Secret: {secret_code}")

client = TitanClient()
# Write to Master's Redis
response = client.store_put("titan_secret_code", secret_code)

if response == "OK":
    print("[PRODUCER] Successfully wrote to Distributed Store.")
else:
    print(f"[PRODUCER] ERROR: Store write failed. Response: {response}")
    sys.exit(1)