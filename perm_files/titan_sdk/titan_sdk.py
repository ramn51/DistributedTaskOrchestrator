import socket
import struct
import base64
import os
import time

# --- CONFIGURATION ---
TITAN_HOST = "127.0.0.1"
TITAN_PORT = 9090
VERSION = 1
OP_SUBMIT_DAG = 4
OP_GET_LOGS = 16

class TitanJob:
    def __init__(self, job_id, filename, job_type="RUN_PAYLOAD", args=None,
             parents=None, port=0):
        self.id = job_id
        self.filename = filename
        self.job_type = job_type
        self.args = args if args else ""
        self.parents = parents if parents else []
        self.port = port
        self.priority = 2
        self.delay = 0
        self.payload_b64 = self._load_file(filename)

    def _load_file(self, filename):
        # --- NEW: ABSOLUTE PATH CHECK ---
        # If filename is "C:\Users\...\args_tester.py", just use it directly!
        if os.path.isabs(filename) and os.path.exists(filename):
             print(f"[SDK] Using Absolute Path: {filename}")
             with open(filename, 'rb') as f: 
                 return base64.b64encode(f.read()).decode('utf-8')
        # --------------------------------

        # ... Existing logic (sdk_dir, search_dirs, etc.) ...
        sdk_dir = os.path.dirname(os.path.abspath(__file__))
        
        search_dirs = [
            os.getcwd(), 
            sdk_dir,
            os.path.abspath(os.path.join(sdk_dir, "..")), 
            r"C:\Users\ASUS\IdeaProjects\DistributedOrchestrator\perm_files"
        ]

        print(f"[SDK] Looking for '{filename}' in: {search_dirs}") # Debug Print

        for d in search_dirs:
            p = os.path.join(d, filename)
            if os.path.exists(p):
                print(f"[SDK] ✅ Found at: {p}")
                with open(p, 'rb') as f: 
                    return base64.b64encode(f.read()).decode('utf-8')
        
        # Crash if not found
        error_msg = f"❌ File '{filename}' not found in any search path."
        raise FileNotFoundError(error_msg)
        

    def to_string(self):
        parents_str = "[" + ",".join(self.parents) + "]"
        
        # FIX: Extract just the filename (e.g. "args_tester.py") from the full path
        simple_filename = os.path.basename(self.filename)

        if self.job_type == "DEPLOY_PAYLOAD":
            payload_content = f"{simple_filename}|{self.payload_b64}|{self.port}"
        else:
            # RUN_PAYLOAD Format: filename | args | base64
            safe_args = self.args.replace("|", " ")
            # Use simple_filename here instead of self.filename
            payload_content = f"{simple_filename}|{safe_args}|{self.payload_b64}"
            
        return f"{self.id}|GENERAL|{self.job_type}|{payload_content}|{self.priority}|{self.delay}|{parents_str}"

class TitanClient:
    def submit_dag(self, name, jobs):
        """Submits a list of TitanJobs as a DAG"""
        print(f"[TitanSDK] Submitting DAG: {name}")
        dag_payload = " ; ".join([j.to_string() for j in jobs])
        return self._send_request(OP_SUBMIT_DAG, dag_payload)

    
    def submit_job(self, job):
        """Helper to submit a single job as a DAG of 1"""
        return self.submit_dag(job.id, [job])
    
    def fetch_logs(self, job_id):
        return self._send_request(OP_GET_LOGS, job_id)

    def _send_request(self, op_code, payload):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((TITAN_HOST, TITAN_PORT))
            payload_bytes = payload.encode('utf-8')
            header = struct.pack('>BBBBI', VERSION, op_code, 0, 0, len(payload_bytes))
            s.sendall(header + payload_bytes)

            s.settimeout(5)
            # Basic Read Loop for response
            response = s.recv(4096).decode('utf-8', errors='ignore')
            s.close()
            return response
        except Exception as e:
            return f"ERROR: {e}"