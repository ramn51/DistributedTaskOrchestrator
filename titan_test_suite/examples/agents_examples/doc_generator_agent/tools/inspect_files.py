from titan_sdk import TitanClient
import json

client = TitanClient()

# REMOVE the 'user:' prefix. Just use the raw key name.
target = "JSON:titan_sdk.py"  # or "JSON:Scheduler.java"

val = client.store_get(target)

if val and val != "NULL" and val != "":
    try:
        # If the worker stored it as a JSON string, we parse it
        data = json.loads(val)
        print(f"📂 File: {data.get('fileName', 'Unknown')}")
        print(f"📝 Content Snippet: {data.get('content', '')[:100]}...")
    except json.JSONDecodeError:
        print(f"📝 Raw Content: {val[:100]}...")
else:
    print(f"❌ JSON not found for key: {target}")
    print("Check if the worker finished or if the filename spelling is exact.")