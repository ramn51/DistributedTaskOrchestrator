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
project_name = "my_titan_project"

from titan_sdk import TitanClient

script_dir = os.path.dirname(os.path.abspath(__file__))

# Construct the path to the asset relative to THIS script
target_file = os.path.join(script_dir, "calc.py")

# 3. Pass the explicit path to the SDK
client = TitanClient()
print(f"Uploading: {target_file}")
resp = client.upload_file(target_file)
print(f"Server: {resp}")