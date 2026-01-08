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

# perm_files/test_runner.py
import sys
import subprocess

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_runner.py <filename_to_test>")
        sys.exit(1)

    target_file = sys.argv[1]
    print(f"[TEST RUNNER] Testing file: {target_file}")

    try:
        # Run the target python file as a subprocess
        result = subprocess.run(
            [sys.executable, target_file],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("[PASS] Execution Successful.")
            print("--- OUTPUT ---")
            print(result.stdout)
        else:
            print("[FAIL] Execution Crashed.")
            print("--- ERROR LOG ---")
            print(result.stderr)

    except Exception as e:
        print(f"[CRITICAL] Test Runner Failed: {e}")