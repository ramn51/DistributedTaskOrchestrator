#!/bin/bash
# package_cloud.sh — Build and package Titan cloud deployment bundles.
#
# Creates two zip files in the project root:
#   titan-master-bundle.zip  — everything needed to run a Titan Master on a cloud VM
#   titan-worker-bundle.zip  — everything needed to run a Titan Worker (remote GPU/CPU)
#
# Usage:
#   chmod +x package_cloud.sh
#   ./package_cloud.sh
#
# Then deploy:
#   Master VM:  scp titan-master-bundle.zip user@master-vm:~/
#               ssh user@master-vm "unzip titan-master-bundle.zip && cd titan-master-bundle && chmod +x start_master.sh && ./start_master.sh"
#
#   Worker VM:  scp titan-worker-bundle.zip user@worker-vm:~/
#               ssh user@worker-vm "unzip titan-worker-bundle.zip && cd titan-worker-bundle && chmod +x start_worker.sh && ./start_worker.sh <MASTER_HOST>"
#
#   RunPod SSH: scp -P <PORT> titan-worker-bundle.zip root@<HOST>:~/
#               (then SSH in, unzip, and run start_worker.sh localhost)

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

ROOT="$(cd "$(dirname "$0")" && pwd)"
JAR="$ROOT/target/titan-orchestrator-1.0-SNAPSHOT.jar"
PERM="$ROOT/perm_files"
STAGING="$ROOT/.bundle_staging"

echo -e "${CYAN}"
echo "  Titan Cloud Bundle Packager"
echo -e "${NC}"

# ─── Step 1: Build JAR if needed ────────────────────────────────────────────
if [ ! -f "$JAR" ]; then
    echo -e "${YELLOW}[BUILD] JAR not found. Building with Maven...${NC}"
    cd "$ROOT"
    mvn clean package -DskipTests > /tmp/titan-build.log 2>&1
    if [ $? -ne 0 ]; then
        echo -e "${RED}[ERROR] Maven build failed. See /tmp/titan-build.log${NC}"
        exit 1
    fi
    echo -e "${GREEN}[OK] Build complete.${NC}"
else
    echo -e "${GREEN}[OK] JAR found: $(basename $JAR)${NC}"
fi

# Sync Worker.jar with the latest build
cp "$JAR" "$PERM/Worker.jar"
echo -e "${GREEN}[OK] Worker.jar updated from latest build.${NC}"

# ─── Step 2: Clean staging area ─────────────────────────────────────────────
rm -rf "$STAGING"
mkdir -p "$STAGING"

# ─── Step 3: Master bundle ───────────────────────────────────────────────────
echo -e "${YELLOW}[PACK] Assembling titan-master-bundle...${NC}"

MASTER_BUNDLE="$STAGING/titan-master-bundle"
MASTER_PERM="$MASTER_BUNDLE/perm_files"

mkdir -p "$MASTER_PERM"
mkdir -p "$MASTER_BUNDLE/uploads"

# Core JARs
cp "$JAR"                       "$MASTER_PERM/titan-orchestrator-1.0-SNAPSHOT.jar"
cp "$PERM/TitanStore.jar"       "$MASTER_PERM/TitanStore.jar"
cp "$PERM/Worker.jar"           "$MASTER_PERM/Worker.jar"

# Dashboard + assets
cp "$PERM/server_dashboard.py"  "$MASTER_PERM/server_dashboard.py"
cp "$PERM/Titan_logo.png"       "$MASTER_PERM/Titan_logo.png"
cp "$PERM/hitl_gate.py"         "$MASTER_PERM/hitl_gate.py"

# Startup script (at bundle root, not inside perm_files)
cp "$PERM/start_master.sh"      "$MASTER_BUNDLE/start_master.sh"
chmod +x "$MASTER_BUNDLE/start_master.sh"

# Touch .gitkeep so uploads/ is preserved in the zip
touch "$MASTER_BUNDLE/uploads/.gitkeep"

# Zip
cd "$STAGING"
zip -r "$ROOT/titan-master-bundle.zip" titan-master-bundle/ -x "*.DS_Store" > /dev/null
echo -e "${GREEN}[OK] titan-master-bundle.zip created.${NC}"

# ─── Step 4: Worker bundle ───────────────────────────────────────────────────
echo -e "${YELLOW}[PACK] Assembling titan-worker-bundle...${NC}"

WORKER_BUNDLE="$STAGING/titan-worker-bundle"
mkdir -p "$WORKER_BUNDLE"

# Worker JAR
cp "$PERM/Worker.jar"   "$WORKER_BUNDLE/Worker.jar"

# SDK (so job scripts can import titan_sdk)
cp -r "$ROOT/titan_sdk" "$WORKER_BUNDLE/titan_sdk"
cp "$ROOT/setup.py"     "$WORKER_BUNDLE/setup.py"

# Startup script
cp "$PERM/start_worker.sh" "$WORKER_BUNDLE/start_worker.sh"
chmod +x "$WORKER_BUNDLE/start_worker.sh"

# Zip
cd "$STAGING"
zip -r "$ROOT/titan-worker-bundle.zip" titan-worker-bundle/ -x "*.DS_Store" -x "*/__pycache__/*" -x "*/.pyc" > /dev/null
echo -e "${GREEN}[OK] titan-worker-bundle.zip created.${NC}"

# ─── Step 5: Cleanup ─────────────────────────────────────────────────────────
rm -rf "$STAGING"

# ─── Summary ─────────────────────────────────────────────────────────────────
MASTER_SIZE=$(du -sh "$ROOT/titan-master-bundle.zip" | cut -f1)
WORKER_SIZE=$(du -sh "$ROOT/titan-worker-bundle.zip" | cut -f1)

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}         Bundles Ready                      ${NC}"
echo -e "${GREEN}============================================${NC}"
echo -e "  titan-master-bundle.zip   ${MASTER_SIZE}"
echo -e "  titan-worker-bundle.zip   ${WORKER_SIZE}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "${CYAN}Deploy to Master VM:${NC}"
echo "  scp titan-master-bundle.zip <USER>@<MASTER_HOST>:~/"
echo "  ssh <USER>@<MASTER_HOST> 'unzip titan-master-bundle.zip && cd titan-master-bundle && chmod +x start_master.sh && ./start_master.sh'"
echo ""
echo -e "${CYAN}Deploy to Worker VM (standard SSH port 22):${NC}"
echo "  scp titan-worker-bundle.zip <USER>@<WORKER_HOST>:~/"
echo "  ssh <USER>@<WORKER_HOST> 'unzip titan-worker-bundle.zip && cd titan-worker-bundle && chmod +x start_worker.sh && ./start_worker.sh <MASTER_HOST>'"
echo ""
echo -e "${CYAN}Deploy to RunPod (SSH over exposed TCP):${NC}"
echo "  scp -P <SSH_PORT> titan-worker-bundle.zip root@<GPU_HOST>:~/"
echo "  ssh -p <SSH_PORT> root@<GPU_HOST> 'unzip titan-worker-bundle.zip && cd titan-worker-bundle && chmod +x start_worker.sh && ./start_worker.sh localhost'"
echo ""
