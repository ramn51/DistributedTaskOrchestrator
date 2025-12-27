import socket
import struct
import json
from flask import Flask, render_template_string

app = Flask(__name__)

# --- CONFIGURATION ---
SCHEDULER_HOST = "127.0.0.1"
SCHEDULER_PORT = 9090
MY_PORT = 5001

# --- TITAN PROTOCOL ---
CURRENT_VERSION = 1
OP_STATS_JSON = 0x09

def recv_all(sock, n):
    data = b''
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet: return None
        data += packet
    return data

def get_titan_stats():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect((SCHEDULER_HOST, SCHEDULER_PORT))

        # Send Request (OP_STATS_JSON, No Payload)
        header = struct.pack('>BBBBI', CURRENT_VERSION, OP_STATS_JSON, 0, 0, 0)
        s.sendall(header)

        # Read Response
        raw_header = recv_all(s, 8)
        if not raw_header: return None
        ver, op, flags, spare, length = struct.unpack('>BBBBI', raw_header)

        if length > 0:
            payload = recv_all(s, length).decode('utf-8')
            # Extract JSON part if there are logs attached
            json_start = payload.find('{')
            if json_start != -1:
                return json.loads(payload[json_start:])
        return None
    except Exception as e:
        print(f"Connection Error: {e}")
        return None

@app.route('/')
def history_view():
    data = get_titan_stats()

    # Flatten the history from all workers into one list
    # Structure: [{'id': 'JOB-1', 'status': 'COMPLETED', 'worker': 8085}, ...]
    all_history = []

    if data and 'workers' in data:
        for w in data['workers']:
            w_port = w.get('port', 'Unknown')
            # Get the history list for this specific worker
            w_hist = w.get('history', [])

            for job in w_hist:
                # Add the worker port to the job object for display
                job['worker'] = w_port
                all_history.append(job)

    # Sort logic (Optional: Currently just order of arrival from JSON)
    # If we had timestamps, we would sort by time here.

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Titan History</title>
        <meta http-equiv="refresh" content="3">
        <style>
            body { background-color: #0f172a; color: #e2e8f0; font-family: sans-serif; padding: 40px; }
            h1 { text-align: center; color: #38bdf8; margin-bottom: 30px; letter-spacing: 1px; }

            .container { max-width: 800px; margin: 0 auto; background: #1e293b; padding: 20px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }

            table { width: 100%; border-collapse: collapse; margin-top: 10px; }
            th { text-align: left; padding: 12px; border-bottom: 2px solid #334155; color: #94a3b8; font-size: 0.85em; text-transform: uppercase; }
            td { padding: 12px; border-bottom: 1px solid #334155; font-family: monospace; font-size: 1.1em; }
            tr:last-child td { border-bottom: none; }
            tr:hover { background-color: #334155; }

            .status-badge { padding: 4px 8px; border-radius: 4px; font-size: 0.7em; font-weight: bold; }
            .status-COMPLETED { background: #064e3b; color: #34d399; }
            .status-FAILED { background: #450a0a; color: #f87171; }
            .status-PENDING { background: #422006; color: #fbbf24; }

            .worker-tag { color: #f472b6; font-weight: bold; }
            .empty-state { text-align: center; padding: 40px; color: #64748b; font-style: italic; }
        </style>
    </head>
    <body>
        <h1>📜 GLOBAL JOB HISTORY</h1>
        <div class="container">
            {% if history %}
            <table>
                <thead>
                    <tr>
                        <th>Job ID</th>
                        <th>Executed On</th>
                        <th>Final Status</th>
                    </tr>
                </thead>
                <tbody>
                    {% for job in history %}
                    <tr>
                        <td style="color: #fff;">{{ job.id }}</td>
                        <td><span class="worker-tag">Node-{{ job.worker }}</span></td>
                        <td><span class="status-badge status-{{ job.status }}">{{ job.status }}</span></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
                <div class="empty-state">No jobs recorded in history yet.</div>
            {% endif %}
        </div>
    </body>
    </html>
    """, history=all_history)

if __name__ == '__main__':
    print(f"Starting History Viewer on http://127.0.0.1:{MY_PORT}")
    app.run(host='0.0.0.0', port=MY_PORT)