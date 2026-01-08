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
import os
import random

def write_chunk(filename, count):
    # FIX: Resolve path relative to THIS script (titan_workspace/shared/)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(base_dir, filename)
    
    print(f"[GEN] Generating {count} numbers into {full_path}...")
    
    with open(full_path, 'w') as f:
        nums = [str(random.randint(1, 100)) for _ in range(count)]
        f.write("\n".join(nums))
        
    print(f"[GEN] Wrote successfully.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: generator.py <file1> <file2>")
        sys.exit(1)

    file1 = sys.argv[1]
    file2 = sys.argv[2]
    
    write_chunk(file1, 50)
    write_chunk(file2, 50)