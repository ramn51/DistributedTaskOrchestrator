#!/bin/bash
# start_master.sh — Start a Titan Master node on a cloud VM.
#
# Run this from the directory where you extracted titan-master-bundle.zip:
#
#   cd ~/titan-master
#   chmod +x start_master.sh
#   ./start_master.sh
#
# Logs: master.log  store.log  dashboard.log  (in the same directory)

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PERM="$SCRIPT_DIR/perm_files"
UPLOADS="$SCRIPT_DIR/uploads"

echo -e "${CYAN}"
echo "  ████████╗██╗████████╗ █████╗ ███╗   ██╗"
echo "     ██╔══╝██║╚══██╔══╝██╔══██╗████╗  ██║"
echo "     ██║   ██║   ██║   ███████║██╔██╗ ██║"
echo "     ██║   ██║   ██║   ██╔══██║██║╚██╗██║"
echo "     ██║   ██║   ██║   ██║  ██║██║ ╚████║"
echo "     ╚═╝   ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═══╝  Master Node"
echo -e "${NC}"

# --- Sanity checks ---
if [ ! -f "$PERM/TitanStore.jar" ]; then
    echo -e "${RED}[ERROR] perm_files/TitanStore.jar not found."
    echo -e "        Run this script from the extracted titan-master-bundle/ directory.${NC}"
    exit 1
fi

if [ ! -f "$PERM/titan-orchestrator-1.0-SNAPSHOT.jar" ]; then
    echo -e "${RED}[ERROR] perm_files/titan-orchestrator-1.0-SNAPSHOT.jar not found.${NC}"
    exit 1
fi

# --- Create uploads dir if missing ---
mkdir -p "$UPLOADS"
echo -e "${GREEN}[OK] uploads/ directory ready.${NC}"

# --- Python / Flask ---
if ! python3 -c "import flask" &>/dev/null; then
    echo -e "${YELLOW}[SETUP] Flask not found. Installing...${NC}"
    pip3 install flask --quiet
fi
echo -e "${GREEN}[OK] Flask ready.${NC}"

# --- Kill any stale processes ---
pkill -f "TitanStore.jar"    2>/dev/null || true
pkill -f "TitanMaster"       2>/dev/null || true
pkill -f "server_dashboard"  2>/dev/null || true
sleep 1

# --- Start TitanStore ---
echo -e "${YELLOW}[START] TitanStore (port 6379)...${NC}"
cd "$SCRIPT_DIR"
java -jar "$PERM/TitanStore.jar" > "$SCRIPT_DIR/store.log" 2>&1 &
STORE_PID=$!
sleep 2

# --- Start Master ---
echo -e "${YELLOW}[START] Titan Master (port 9090)...${NC}"
java -cp "$PERM/titan-orchestrator-1.0-SNAPSHOT.jar" titan.TitanMaster > "$SCRIPT_DIR/master.log" 2>&1 &
MASTER_PID=$!
sleep 2

# --- Start Dashboard ---
echo -e "${YELLOW}[START] Dashboard (port 5000)...${NC}"
python3 "$PERM/server_dashboard.py" > "$SCRIPT_DIR/dashboard.log" 2>&1 &
DASH_PID=$!
sleep 1

# --- Verify ---
if ! kill -0 $MASTER_PID 2>/dev/null; then
    echo -e "${RED}[ERROR] Master failed to start. Check master.log${NC}"
    exit 1
fi

echo -e "\n${GREEN}============================================${NC}"
echo -e "${GREEN}         TITAN MASTER NODE IS LIVE          ${NC}"
echo -e "${GREEN}============================================${NC}"
echo -e "  TitanStore : localhost:6379   (PID: $STORE_PID)"
echo -e "  Master     : 0.0.0.0:9090    (PID: $MASTER_PID)"
echo -e "  Dashboard  : http://0.0.0.0:5000  (PID: $DASH_PID)"
echo -e "${GREEN}============================================${NC}"
echo -e "  Logs:"
echo -e "    tail -f $SCRIPT_DIR/master.log"
echo -e "    tail -f $SCRIPT_DIR/store.log"
echo -e "    tail -f $SCRIPT_DIR/dashboard.log"
echo -e "${GREEN}============================================${NC}"
echo -e "${YELLOW}[INFO] To stop all services:${NC}"
echo -e "  pkill -f TitanStore ; pkill -f TitanMaster ; pkill -f server_dashboard"
