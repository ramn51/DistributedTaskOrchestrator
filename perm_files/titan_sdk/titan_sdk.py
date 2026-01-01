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
    def __init__(self, job_id, filename, job_type="RUN_PAYLOAD", parents=None, port=0):
        self.id = job_id
        self.filename = filename
        self.job_type = job_type
        self.parents = parents if parents else []
        self.port = port
        self.priority = 2
        self.delay = 0
        self.payload_b64 = self._load_file(filename)

    def _load_file(self, filename):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        search_dirs = [
            script_dir,
            os.path.abspath(os.path.join(script_dir, "..")),
            r"C:\Users\ASUS\IdeaProjects\DistributedOrchestrator\perm_files"
        ]
        for d in search_dirs:
            p = os.path.join(d, filename)
            if os.path.exists(p):
                with open(p, 'rb') as f: return base64.b64encode(f.read()).decode('utf-8')
        return "UEsDBA==" # Dummy

    def to_string(self):
        parents_str = "[" + ",".join(self.parents) + "]"
        if self.job_type == "DEPLOY_PAYLOAD":
            payload_content = f"{self.filename}|{self.payload_b64}|{self.port}"
        else:
            payload_content = f"{self.filename}|{self.payload_b64}"
        return f"{self.id}|GENERAL|{self.job_type}|{payload_content}|{self.priority}|{self.delay}|{parents_str}"

class TitanClient:
    def submit_dag(self, name, jobs):
        """Submits a list of TitanJobs as a DAG"""
        print(f"🚀 [TitanSDK] Submitting DAG: {name}")
        dag_payload = " ; ".join([j.to_string() for j in jobs])
        return self._send_request(OP_SUBMIT_DAG, dag_payload)

    def fetch_logs(self, job_id):
        """Asks Titan Master for the logs of a specific Job"""
        # NOTE: You need to ensure OP_GET_LOGS (18) is implemented in SchedulerServer.java
        # If not, use OP_STATS or implement a new OpCode.
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