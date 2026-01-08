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

import socket
import struct
import base64
import time
import os

# CONFIG
HOST = "127.0.0.1"
PORT = 9090
VERSION = 1
OP_SUBMIT_DAG = 4

def get_base64_payloads():
    # Helper to load local files for the payload.
    # Adjust paths if your script is in a different folder structure.
    # Here we just use a simple dummy script to prove the scheduling logic works.

    dummy_script = "print('Running Affinity Task on Worker...')"
    dummy_b64 = base64.b64encode(dummy_script.encode('utf-8')).decode('utf-8')
    return dummy_b64

def send_affinity_dag():
    script_b64 = get_base64_payloads()

    print(f"🚀 Constructing AFFINITY DAG...")

    # DAG STRUCTURE:
    # 1. JOB_TRAIN (Parent) -> Runs on any available worker (Load Balanced)
    # 2. JOB_TEST  (Child)  -> DEPENDS ON [JOB_TRAIN] AND HAS |AFFINITY flag

    # NOTE: We append '|AFFINITY' at the very end.
    # The 'Job.fromDagString' parser in Java will detect this flag.

    dag = (
        # JOB 1: THE TRAINER (Parent)
        # Format: ID | SKILL | PAYLOAD_TYPE | filename | b64 | Priority | Delay | [Parents]
        f"JOB_TRAIN|GENERAL|RUN_PAYLOAD|train_model.py|{script_b64}|5|0|[] ; "

        # JOB 2: THE TESTER (Child) - MUST RUN ON SAME NODE
        # Format: ... | [Parents] | AFFINITY
        f"JOB_TEST|GENERAL|RUN_PAYLOAD|test_model.py|{script_b64}|5|0|[JOB_TRAIN]|AFFINITY"
    )

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))

        payload_bytes = dag.encode('utf-8')
        # Header: Ver | Op | Flags | Spare | Length
        header = struct.pack('>BBBBI', VERSION, OP_SUBMIT_DAG, 0, 0, len(payload_bytes))

        s.sendall(header + payload_bytes)

        # Read Ack
        s.settimeout(5)
        resp_header = s.recv(8)

        if resp_header:
            print(f"✅ Affinity DAG Submitted!")
            print("   Structure: JOB_TRAIN --> JOB_TEST (Sticky)")
            print("   EXPECTATION: Both jobs must execute on the SAME Worker Port.")
        else:
            print(f"❌ Submission Failed (No ACK).")

        s.close()
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    send_affinity_dag()