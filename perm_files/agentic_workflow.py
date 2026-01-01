import socket
import struct
import base64
import os
import time

# CONFIG
HOST = "127.0.0.1"
PORT = 9090

# PROTOCOL CONSTANTS
VERSION = 1
OP_SUBMIT_DAG = 4  # Ensure this matches TitanProtocol.java

def get_file_payload(filepath):
    """Helper to safely read a file and convert to Base64"""
    if not os.path.exists(filepath):
        print(f"⚠️ Warning: File not found {filepath}. Using dummy content.")
        return "DUMMY_DATA"

    with open(filepath, 'rb') as f:
        raw_bytes = f.read()
        return base64.b64encode(raw_bytes).decode('utf-8')

def run_architect():
    # Define paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    perm_dir = base_dir

    # 1. Load generate.py
    gen_script_path = os.path.join(perm_dir, "generate_code.py")
    gen_script_b64 = get_file_payload(gen_script_path)

    print(f"🚀 Architect Agent Starting...")
    print(f"📦 Loaded generate.py payload size: {len(gen_script_b64)} bytes")

    # 2. Construct the Agentic Plan (The DAG)
    # Note: Using your format: ID|SKILL|CMD|FILE|B64|PRIORITY|DELAY|DEPS
    dag_plan = (
        # JOB 1: Generate Game Logic
        f"GEN_LOGIC|GENERAL|RUN_PAYLOAD|generate_code.py|{gen_script_b64}|2|0|[] ; "

        # JOB 2: Generate UI
        f"GEN_UI|GENERAL|RUN_PAYLOAD|generate_code.py|{gen_script_b64}|2|0|[] ; "

        # JOB 3: Merge (Waits for Logic + UI)
        f"JOB_MERGE|GENERAL|RUN_PAYLOAD|generate_code.py|{gen_script_b64}|1|0|[GEN_LOGIC,GEN_UI]"
    )

    # 3. Send to Titan
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))

        payload_bytes = dag_plan.encode('utf-8')

        # --- FIX: USE THE EXACT 8-BYTE HEADER FROM YOUR WORKING SCRIPT ---
        # Structure: > (Big Endian) B (Ver) B (Op) B (Flags) B (Spare) I (Int Length)
        header = struct.pack('>BBBBI', VERSION, OP_SUBMIT_DAG, 0, 0, len(payload_bytes))

        # Send Header + Payload
        s.sendall(header + payload_bytes)

        # Read Response (Timeout ensures we don't hang if server is silent)
        s.settimeout(5)
        try:
            # Assuming server sends back a similar header or just data.
            # Your working script reads 8 bytes first, so we do the same.
            resp_header = s.recv(8)
            if resp_header:
                print(f"✅ Plan Submitted Successfully!")
            else:
                print(f"⚠️ Server closed connection without data.")
        except socket.timeout:
            print("⚠️ No response from server (Timeout), but data likely sent.")

        s.close()

    except Exception as e:
        print(f"❌ Connection Failed: {e}")

if __name__ == "__main__":
    run_architect()