#!/bin/bash
# start_worker.sh — Start a Titan Worker on a remote GPU/CPU node.
#
# Usage:
#   chmod +x start_worker.sh
#   ./start_worker.sh <MASTER_HOST> [WORKER_PORT] [WORKER_TYPE] [PERMANENT]
#
# Examples:
#   ./start_worker.sh 10.0.0.1               # GPU worker, port 8085, permanent
#   ./start_worker.sh 10.0.0.1 8086 GENERAL  # GENERAL worker on port 8086
#   ./start_worker.sh localhost 8085 GPU true # For SSH tunnel setup (RunPod)
#
# Arguments:
#   MASTER_HOST   IP or hostname of the Titan Master (required)
#   WORKER_PORT   Port this worker listens on (default: 8085)
#   WORKER_TYPE   GENERAL | GPU | HIGH_MEM (default: GPU)
#   PERMANENT     true | false — re-register after job completion (default: true)

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

MASTER_HOST="${1:-}"
WORKER_PORT="${2:-8085}"
WORKER_TYPE="${3:-GPU}"
PERMANENT="${4:-true}"
MASTER_PORT=9090

if [ -z "$MASTER_HOST" ]; then
    echo -e "${RED}[ERROR] MASTER_HOST is required.${NC}"
    echo ""
    echo "Usage: ./start_worker.sh <MASTER_HOST> [WORKER_PORT] [WORKER_TYPE] [PERMANENT]"
    echo ""
    echo "Examples:"
    echo "  ./start_worker.sh 10.0.0.1               # GPU worker on port 8085"
    echo "  ./start_worker.sh localhost 8085 GPU true # SSH tunnel (RunPod)"
    echo "  ./start_worker.sh 10.0.0.1 8086 GENERAL  # GENERAL worker"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo -e "${CYAN}[INFO] Titan Worker starting...${NC}"
echo -e "  Master     : ${MASTER_HOST}:${MASTER_PORT}"
echo -e "  Worker port: ${WORKER_PORT}"
echo -e "  Type       : ${WORKER_TYPE}"
echo -e "  Permanent  : ${PERMANENT}"
echo ""

# --- Java check ---
if ! command -v java &>/dev/null; then
    echo -e "${RED}[ERROR] Java not found. Install with: apt install openjdk-17-jdk${NC}"
    exit 1
fi

# --- Python alias check ---
if ! command -v python &>/dev/null; then
    echo -e "${YELLOW}[WARN] 'python' command not found. Titan workers need it to execute jobs.${NC}"
    echo -e "${YELLOW}       Install with: apt install -y python-is-python3${NC}"
fi

# --- Install titan_sdk if present ---
if [ -f "$SCRIPT_DIR/setup.py" ]; then
    echo -e "${YELLOW}[SETUP] Installing titan_sdk...${NC}"
    pip install -e "$SCRIPT_DIR" --quiet
    echo -e "${GREEN}[OK] titan_sdk installed.${NC}"
fi

# --- Set env so Python job scripts can reach Master via tunnel ---
export TITAN_HOST="$MASTER_HOST"
export TITAN_PORT="$MASTER_PORT"
echo -e "${GREEN}[OK] TITAN_HOST=${TITAN_HOST}  TITAN_PORT=${TITAN_PORT}${NC}"

# --- Start worker ---
echo -e "${YELLOW}[START] Launching TitanWorker...${NC}"
java -cp "$SCRIPT_DIR/Worker.jar" titan.TitanWorker \
    "$WORKER_PORT" "$MASTER_HOST" "$MASTER_PORT" "$WORKER_TYPE" "$PERMANENT"
