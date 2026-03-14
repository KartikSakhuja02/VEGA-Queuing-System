#!/bin/bash
set -euo pipefail

echo "=================================================="
echo "VEGA Queue - Raspberry Pi Setup"
echo "=================================================="
echo ""

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="vega-queue"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}.service"
CURRENT_USER="${SUDO_USER:-$USER}"

if ! command -v apt >/dev/null 2>&1; then
    echo "This script is intended for Debian/Ubuntu/Raspberry Pi OS."
    exit 1
fi

echo "Project directory: ${PROJECT_DIR}"
echo "Service name: ${SERVICE_NAME}"
echo ""

echo "Step 1/7: Installing system dependencies..."
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git libjpeg-dev zlib1g-dev libpng-dev

echo ""
echo "Step 2/7: Ensuring swap to avoid pip OOM kills..."
if ! sudo swapon --show | grep -q .; then
    echo "No active swap detected. Creating /swapfile (1G)..."
    sudo fallocate -l 1G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    if ! grep -q '^/swapfile ' /etc/fstab; then
        echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
    fi
else
    echo "Swap is already active."
fi

echo ""
echo "Step 3/7: Creating virtual environment (if missing)..."
if [ ! -d "${PROJECT_DIR}/venv" ]; then
    python3 -m venv "${PROJECT_DIR}/venv"
fi

echo ""
echo "Step 4/7: Installing Python dependencies safely..."
source "${PROJECT_DIR}/venv/bin/activate"
python -m pip install --upgrade pip setuptools wheel

# Install heavier packages one by one with no-cache to reduce RAM usage.
python -m pip install --no-cache-dir "discord.py>=2.3.0"
python -m pip install --no-cache-dir "python-dotenv>=1.0.0"
python -m pip install --no-cache-dir "asyncpg>=0.29.0"
python -m pip install --no-cache-dir "google-generativeai>=0.3.0"
python -m pip install --no-cache-dir "Pillow>=10.0.0"

echo ""
echo "Step 5/7: Preparing logs directory..."
mkdir -p "${PROJECT_DIR}/logs"

echo ""
echo "Step 6/7: Installing ${SERVICE_NAME}.service..."
sudo tee "${SERVICE_PATH}" >/dev/null <<EOF
[Unit]
Description=VEGA Queue Discord Bot
After=network.target

[Service]
Type=simple
User=${CURRENT_USER}
WorkingDirectory=${PROJECT_DIR}
ExecStart=${PROJECT_DIR}/venv/bin/python ${PROJECT_DIR}/bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo ""
echo "Step 7/7: Enabling and starting service..."
sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}"
sudo systemctl restart "${SERVICE_NAME}"
sudo systemctl --no-pager status "${SERVICE_NAME}" | head -n 20

echo ""
echo "=================================================="
echo "Setup complete"
echo "=================================================="
echo "Service logs: sudo journalctl -u ${SERVICE_NAME} -f"
echo ""
