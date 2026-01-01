import socket
import struct
import base64
import os
import json
import time

# --- CONFIGURATION ---
TITAN_HOST = "127.0.0.1"
TITAN_PORT = 9090
VERSION = 1
OP_SUBMIT_DAG = 4

# --- THE SDK (Software Development Kit) ---

class TitanJob:
    def __init__(self, job_id, filename, job_type="RUN_PAYLOAD", parents=None, port=0):
        self.id = job_id
        self.filename = filename
        self.job_type = job_type  # RUN_PAYLOAD, DEPLOY_PAYLOAD, PDF_CONVERT
        self.parents = parents if parents else []
        self.port = port
        self.priority = 2
        self.delay = 0
        self.payload_b64 = self._load_file(filename)

    def _load_file(self, filename):
        # Auto-discovery logic (Same as your fixed script)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        search_dirs = [
            script_dir,
            os.path.abspath(os.path.join(script_dir, "..")),
            r"C:\Users\ASUS\IdeaProjects\DistributedOrchestrator\perm_files"
        ]

        target_path = None
        for d in search_dirs:
            p = os.path.join(d, filename)
            if os.path.exists(p):
                target_path = p
                break

        if not target_path:
            print(f"⚠️ Warning: {filename} not found. Sending dummy.")
            return "UEsDBA==" # Safe Dummy

        with open(target_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')

    def to_string(self):
        # Format: ID|SKILL|TYPE|FILE|B64|PORT|PRI|DELAY|[PARENTS]
        parents_str = "[" + ",".join(self.parents) + "]"

        # Determine strict payload structure
        if self.job_type == "DEPLOY_PAYLOAD":
            # DEPLOY format: filename|b64|port
            payload_content = f"{self.filename}|{self.payload_b64}|{self.port}"
        else:
            # RUN format: filename|b64
            payload_content = f"{self.filename}|{self.payload_b64}"

        return f"{self.id}|GENERAL|{self.job_type}|{payload_content}|{self.priority}|{self.delay}|{parents_str}"


class TitanDAG:
    def __init__(self, name):
        self.name = name
        self.jobs = []

    def add_step(self, job_id, script_name, depends_on=None, operation="RUN_PAYLOAD", port=0):
        job = TitanJob(job_id, script_name, operation, depends_on, port)
        self.jobs.append(job)
        return job

    def submit(self):
        print(f"🚀 Compiling DAG: {self.name} ({len(self.jobs)} steps)...")

        # Combine all jobs with " ; " delimiter
        dag_payload = " ; ".join([j.to_string() for j in self.jobs])

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((TITAN_HOST, TITAN_PORT))

            payload_bytes = dag_payload.encode('utf-8')
            header = struct.pack('>BBBBI', VERSION, OP_SUBMIT_DAG, 0, 0, len(payload_bytes))

            s.sendall(header + payload_bytes)

            s.settimeout(5)
            if s.recv(8):
                print(f"✅ DAG '{self.name}' Submitted Successfully!")
            else:
                print(f"❌ Server closed connection.")
            s.close()
        except Exception as e:
            print(f"❌ Connection Error: {e}")

# --- THE AGENTIC RUNTIME (The "Brain") ---

def mock_llm_planner(user_prompt):
    """
    Simulates an LLM receiving a prompt and returning a structured plan.
    """
    print(f"🤖 AI Agent received prompt: '{user_prompt}'")
    time.sleep(1) # Thinking...
    print("🤖 AI Agent is devising a execution plan...")

    # Dynamic Decision Logic (Mocked)
    if "snake" in user_prompt.lower():
        return {
            "project": "SnakeGame",
            "steps": [
                {"id": "GEN_LOGIC", "script": "generate_code.py", "type": "RUN_PAYLOAD"},
                {"id": "GEN_UI",    "script": "generate_code.py", "type": "RUN_PAYLOAD"},
                {"id": "MERGE",     "script": "generate_code.py", "type": "RUN_PAYLOAD", "deps": ["GEN_LOGIC", "GEN_UI"]}
            ]
        }
    elif "deploy" in user_prompt.lower():
        return {
            "project": "InfrastructureDeploy",
            "steps": [
                {"id": "SPAWN_WORKER", "script": "Worker.jar", "type": "DEPLOY_PAYLOAD", "port": 8086},
                {"id": "RUN_CALC",     "script": "calc.py",    "type": "RUN_PAYLOAD"},
                {"id": "DEPLOY_SVC",   "script": "log_viewer.py", "type": "DEPLOY_PAYLOAD", "port": 9991, "deps": ["RUN_CALC"]}
            ]
        }
    else:
        return None

def execute_agent_runtime():
    # 1. User Input
    user_goal = "I want to build a Snake game using the agentic swarm."
    # user_goal = "Deploy a logging service infrastructure."

    # 2. Agent Plans
    plan = mock_llm_planner(user_goal)

    if not plan:
        print("❌ Agent could not understand the request.")
        return

    # 3. Runtime Builds DAG
    dag = TitanDAG(plan["project"])

    print(f"📋 Blueprint Created: {plan['project']}")
    for step in plan["steps"]:
        # Auto-prefix IDs with 'DAG-' for shared context safety
        step_id = f"DAG-{step['id']}"
        deps = [f"DAG-{d}" for d in step.get("deps", [])]

        dag.add_step(
            job_id=step_id,
            script_name=step['script'],
            depends_on=deps,
            operation=step['type'],
            port=step.get('port', 0)
        )
        print(f"   + Added Step: {step_id} -> {step['script']}")

    # 4. Execute
    dag.submit()

if __name__ == "__main__":
    execute_agent_runtime()