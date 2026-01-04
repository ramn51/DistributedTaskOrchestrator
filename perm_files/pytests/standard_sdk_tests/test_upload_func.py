import os
project_name = "my_titan_project"
script_dir = os.path.dirname(os.path.abspath(__file__))
project_path = os.path.join(script_dir, project_name)

from titan_sdk.titan_sdk import TitanClient

script_dir = os.path.dirname(os.path.abspath(__file__))

# Construct the path to the asset relative to THIS script
target_file = os.path.join(script_dir, "new_calc_version.py")

# 3. Pass the explicit path to the SDK
client = TitanClient()
print(f"Uploading: {target_file}")
resp = client.upload_file(target_file)
print(f"Server: {resp}")