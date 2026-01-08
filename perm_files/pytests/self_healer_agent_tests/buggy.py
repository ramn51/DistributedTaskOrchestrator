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

# perm_files/buggy_math.py
import sys

def calculate_stats(numbers):
    # BUG: This crashes if the list is empty (ZeroDivisionError)
    avg = sum(numbers) / len(numbers)
    return avg

if __name__ == "__main__":
    data = [] # Empty list causing the crash
    print(f"Analyzing Data...")
    print(f"Average: {calculate_stats(data)}")