import sys
import json
from titan_sdk import TitanClient

def main():
    if len(sys.argv) < 2:
        return
    
    # Arg is the RAW key (e.g., "RAW:Scheduler.java")
    raw_key = sys.argv[1]
    client = TitanClient()
    
    # 1. Fetch Raw Content
    print(f"Fetching {raw_key} from Titan Store...")
    content = client.store_get(raw_key)
    
    if not content or content == "NULL":
        print(f"Key {raw_key} not found.")
        return

    # 2. Wrap in JSON
    filename = raw_key.split(":", 1)[1]
    data = {
        "fileName": filename,
        "content": content,
        "status": "PENDING_METHOD_EXTRACTION"
    }
    
    # 3. Store the JSON object
    json_key = f"JSON:{filename}"
    client.store_put(json_key, json.dumps(data))
    
    print(f"Created JSON wrap for {filename} at key: {json_key}")

if __name__ == "__main__":
    main()