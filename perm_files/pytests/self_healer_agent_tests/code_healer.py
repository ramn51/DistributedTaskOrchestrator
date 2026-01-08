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

import time
import json
import os
import google.generativeai as genai
from titan_sdk import TitanClient, TitanJob

import dotenv
dotenv.load_dotenv()

# --- CONFIGURATION ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)

model = genai.GenerativeModel('models/gemini-2.0-flash-lite-001')

# --- THE DOCTOR'S BRAIN ---
SYSTEM_PROMPT = """
You are the "Code Healer", a specialized debugging agent on Titan.
Your ONLY goal is to fix crashing Python scripts.

AVAILABLE TOOLS:
1. TEST: Runs a script to see if it works.
   - Action: "RUN", file: "test_runner.py", args: "<target_file>"
   
2. READ: Reads the content of a file.
   - Action: "RUN", file: "file_manager.py", args: "READ <target_file>"

3. WRITE: Overwrites a file with fixed code.
   - Action: "RUN", file: "file_manager.py", args: "WRITE <target_file> <BASE64_CONTENT>"

STRATEGY (The Debug Loop):
1. DIAGNOSE: Run 'test_runner.py' on the target.
2. ANALYZE: If it fails, Read the file. Look at the Error Log.
3. FIX: Rewrite the file with the fix.
4. VERIFY: Run 'test_runner.py' again.
5. FINISH: If the logs show "[PASS]", return action "FINISH".

OUTPUT FORMAT:
Strictly return a JSON object. No markdown.
{
  "action": "SUBMIT" or "FINISH",
  "comment": "Short reasoning",
  "jobs": [ { "file": "...", "args": "..." } ]
}
"""

def clean_json_response(response_text):
    """Helper to strip markdown ```json ... ```"""
    clean_text = response_text.strip()
    if clean_text.startswith("```json"):
        clean_text = clean_text.replace("```json", "").replace("```", "")
    elif clean_text.startswith("```"):
         clean_text = clean_text.replace("```", "")
    return clean_text

def ask_doctor(history, user_goal, attempt, max_retries=3):
    full_prompt = f"{SYSTEM_PROMPT}\n\nCURRENT GOAL: {user_goal}\n\n"
    
    # Add History Context
    if history:
        full_prompt += "--- PREVIOUS ATTEMPTS & LOGS ---\n"
        for log in history:
            full_prompt += f"{log}\n"
    
    full_prompt += "\n\nProvide the next JSON Action Plan:"

    try:
        # Call Gemini
        response = model.generate_content(
            full_prompt,
            generation_config={"response_mime_type": "application/json"} # Forces JSON
        )
        
        raw_text = response.text
        return json.loads(clean_json_response(raw_text))
        
    except Exception as e:
        if "429" in str(e) or "quota" in str(e).lower():
                print(f"⚠️ Quota exceeded. Sleeping for 60s... (Attempt {attempt+1}/{max_retries})")
                time.sleep(60)

        else:
            print(f"❌ Gemini Error: {e}")
            # Return a safe fallback so the loop doesn't crash
            return {"action": "WAIT", "comment": "API Error, retrying...", "jobs": []}

def run_healer(target_file):
    titan = TitanClient()
    history = []
    
    print(f"🚑 HEALER DISPATCHED for: {target_file}")
    
    for i in range(3): # Max 5 attempts to fix
        print(f"\n--- Cycle {i+1} ---")
        
        # 1. Ask the Doctor what to do
        plan = ask_doctor(history, f"The file {target_file} is broken. Fix it.", i, max_retries=3)
        print(f"💊 Prescription: {plan.get('comment')}")
        
        if plan['action'] == "FINISH":
            print("✅ PATIENT CURED! Exiting.")
            return

        # 2. Execute the treatment
        jobs = []
        for j in plan['jobs']:
            # IMPORTANT: The ID you give here will get "DAG-" added by the server 
            # OR you can add it explicitly here to be safe.
            job_id_local = f"HEAL_{i}_{j['file'][:4]}"
            job = TitanJob(
                job_id=job_id_local,
                filename=j['file'],
                job_type="RUN_PAYLOAD",
                args=j.get('args', "") # <--- Uses your new Args feature!
            )
            jobs.append(job)

        titan.submit_dag(f"Healer_Batch_{i}", jobs)
        
        # 3. Read the Chart (Logs)
        time.sleep(4) # Wait for execution
        cycle_log = ""
        for j in jobs:
            log = titan.fetch_logs(j.id)
            print(f"   📋 Result: {log.strip()[:100]}...")
            cycle_log += f"Job {j.filename} Result:\n{log}\n"
        
        history.append(cycle_log)

if __name__ == "__main__":
    # Make sure you have 'buggy_math.py' created first!
    run_healer("buggy_math.py")