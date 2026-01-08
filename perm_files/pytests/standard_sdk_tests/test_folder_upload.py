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

import os, sys
import shutil


# 1. Setup a dummy project folder
project_name = "my_titan_project"

from titan_sdk.titan_sdk import TitanClient

if not os.path.exists(project_path):
    os.makedirs(project_path)
    # Create a few dummy files
    with open(os.path.join(project_path, "main.py"), "w") as f:
        f.write("print('Main running')")
    with open(os.path.join(project_path, "helper.py"), "w") as f:
        f.write("print('Helper loaded')")
    print(f"📁 Created test folder at: {project_path}")

# 2. Upload it using the SDK
client = TitanClient()
print(f"🚀 Uploading Project Folder: {project_name}...")

# This should Zip -> Upload -> Return Success
resp = client.upload_project_folder(project_path)
print(f"Server Response: {resp}")

# 3. Cleanup (Optional)
# shutil.rmtree(project_path)