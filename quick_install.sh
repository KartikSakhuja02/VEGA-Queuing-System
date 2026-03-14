#!/bin/bash
# Quick install script for Raspberry Pi - installs specific versions to avoid memory issues

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=================================================="
echo "VEGA Queue - Quick Installer for RPi"
echo "=================================================="
echo ""

if [ -d "${PROJECT_DIR}/venv" ]; then
	# shellcheck disable=SC1091
	source "${PROJECT_DIR}/venv/bin/activate"
fi

echo "Step 1: Installing packages with specific versions (no dependency resolution)..."

# Install with exact versions to avoid pip resolver consuming all RAM
python -m pip install --no-cache-dir google-generativeai==0.8.0
python -m pip install --no-cache-dir Pillow==10.2.0

echo ""
echo "=================================================="
echo "✅ Installation complete!"
echo "=================================================="
echo ""
