import socket
import struct
import sys

def titan_read(sock):
    try:
        # Java's writeInt sends 4 bytes
        raw_len = sock.recv(4)
        if not raw_len:
            print("[FAIL] Error: No length prefix received.")
            return None

        # '>I' means Big-Endian Unsigned Integer (Standard for Java)
        msg_len = struct.unpack('>I', raw_len)[0]

        chunks = []
        bytes_recd = 0
        while bytes_recd < msg_len:
            chunk = sock.recv(min(msg_len - bytes_recd, 4096))
            if not chunk: break
            chunks.append(chunk)
            bytes_recd += len(chunk)

        return b"".join(chunks).decode('utf-8')
    except Exception as e:
        print(f"[FAIL] Read Error: {e}")
        return None

def verify_titan():
    print("--- STARTING TITAN VALIDATION ---")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect(("localhost", 9090))
            print("Connected to Scheduler.")

            # 1. Send Command with Length Prefix
            cmd = "STATS_JSON"
            payload = cmd.encode('utf-8')
            # Pack length as 4-byte big-endian int
            header = struct.pack('>I', len(payload))
            s.sendall(header + payload)
            print(f"Sent: {cmd}")

            # 2. Read Response
            result = titan_read(s)
            if result:
                print("[OK] DATA RECEIVED:")
                print(result)
            else:
                print("⚠️ Received empty string from Scheduler.")

    except Exception as e:
        print(f"[FAIL] CONNECTION FAILED: {e}")

    print("--- DIAGNOSTIC COMPLETE ---")

if __name__ == "__main__":
    verify_titan()