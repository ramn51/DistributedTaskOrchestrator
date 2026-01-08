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

def main():
    print("--- ARGUMENT TEST START ---")

    # sys.argv[0] is always the script name itself
    print(f"Script Name: {sys.argv[0]}")

    # Check if we received args
    if len(sys.argv) > 1:
        print(f"Total Arguments Received: {len(sys.argv) - 1}")

        # Loop through and print each arg with its index
        for i, arg in enumerate(sys.argv[1:], start=1):
            print(f"Arg #{i}: {arg}")
    else:
        print("FAIL: No arguments were passed!")

    print("--- ARGUMENT TEST END ---")

if __name__ == "__main__":
    main()