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
import base64

def read_file(filepath):
    """Reads a file and prints its content for the Agent to see."""
    try:
        if not os.path.exists(filepath):
            print(f"[ERROR] File not found: {filepath}")
            sys.exit(1)
            
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        print(f"--- BEGIN FILE CONTENT: {filepath} ---")
        print(content)
        print(f"--- END FILE CONTENT ---")
        
    except Exception as e:
        print(f"[ERROR] Failed to read file: {e}")
        sys.exit(1)

def write_file(filepath, b64_content):
    """Decodes Base64 content and overwrites the target file."""
    try:
        # decode base64 back to raw text
        decoded_bytes = base64.b64decode(b64_content)
        decoded_str = decoded_bytes.decode('utf-8')
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(decoded_str)
            
        print(f"[SUCCESS] Written {len(decoded_str)} characters to {filepath}")
        
    except Exception as e:
        print(f"[ERROR] Failed to write file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Usage: python file_manager.py <COMMAND> <FILENAME> [CONTENT_B64]
    
    if len(sys.argv) < 3:
        print("Usage: python file_manager.py [READ|WRITE] <filename> <content_if_write>")
        sys.exit(1)

    command = sys.argv[1].upper()
    filename = sys.argv[2]

    # Resolve path relative to current working directory (titan_workspace/shared or job folder)
    target_path = os.path.abspath(filename)
    print(f"[FILE_MANAGER] Target: {target_path}")

    if command == "READ":
        read_file(target_path)
        
    elif command == "WRITE":
        if len(sys.argv) < 4:
            print("[ERROR] WRITE command requires Base64 content argument.")
            sys.exit(1)
        
        content = sys.argv[3]
        write_file(target_path, content)
        
    else:
        print(f"[ERROR] Unknown command: {command}")
        sys.exit(1)