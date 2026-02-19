import sys
import os
import requests
import json

# --- CONFIGURATION ---
# Get API Key from Environment (Set this in your Worker's env or hardcode for local dev)
API_KEY = os.getenv("GEMINI_API_KEY") 
# Gemini Endpoint
LLM_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"

def generate_documented_code(file_path, code_content):
    language = "Java" if file_path.endswith(".java") else "Python"
    doc_style = "Javadoc" if language == "Java" else "Python Docstrings"

    prompt = f"""
    You are an expert Senior Software Engineer.
    
    TASK: Refactor the following {language} code to add high-quality {doc_style} to all classes and methods.
    
    RULES:
    1. Do NOT change any logic, variable names, or behavior.
    2. ONLY add comments/docs.
    3. Return the FULL code file, ready to be saved.
    4. Do not wrap the output in markdown code blocks (like ```java). Return RAW text.
    
    CODE:
    {code_content}
    """

    payload = { "contents": [{"parts": [{"text": prompt}]}] }

    try:
        response = requests.post(LLM_URL, json=payload, headers={'Content-Type': 'application/json'})
        if response.status_code == 200:
            data = response.json()
            raw_text = data['candidates'][0]['content']['parts'][0]['text']
            
            # Clean up potential Markdown wrappers if the LLM ignores Rule 4
            if raw_text.startswith("```"):
                lines = raw_text.splitlines()
                # Remove first line (```java) and last line (```)
                if lines[0].startswith("```"): lines = lines[1:]
                if lines[-1].startswith("```"): lines = lines[:-1]
                return "\n".join(lines)
            return raw_text
        else:
            print(f"❌ [API ERROR] {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"❌ [EXCEPTION] {e}")
        return None

# --- MAIN LOGIC ---

if len(sys.argv) < 2:
    print("Usage: doc_worker.py <filepath>")
    sys.exit(1)

file_path = sys.argv[1]
print(f"🤖 [WORKER] Processing {os.path.basename(file_path)}...")

if not API_KEY:
    print("❌ [ERROR] No API Key found. Skipping.")
    sys.exit(1)

# 1. Read Original Code
try:
    with open(file_path, "r", encoding="utf-8") as f:
        original_code = f.read()
except Exception as e:
    print(f"❌ [ERROR] Read failed: {e}")
    sys.exit(1)

# 2. Call AI
new_code = generate_documented_code(file_path, original_code)

if new_code:
    # 3. Safety Check: Don't overwrite if it looks empty or too small
    if len(new_code) < len(original_code) * 0.5:
        print("⚠️ [SAFETY] Generated code is suspiciously short. Aborting overwrite.")
        sys.exit(1)

    # 4. Overwrite File
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_code)
    print(f"✅ [SUCCESS] Documentation added to {os.path.basename(file_path)}")
else:
    print("❌ [FAIL] No code generated.")
    sys.exit(1)