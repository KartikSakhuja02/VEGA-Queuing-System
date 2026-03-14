#!/bin/bash
# Install google-generativeai packages one by one to avoid crashes

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=================================================="
echo "Installing Google Generative AI - One by One"
echo "=================================================="
echo ""

cd "${PROJECT_DIR}"
# shellcheck disable=SC1091
source "${PROJECT_DIR}/venv/bin/activate"

echo "Step 1: Installing protobuf..."
python -m pip install --no-cache-dir protobuf==5.29.6
sleep 2

echo ""
echo "Step 2: Installing typing-extensions..."
python -m pip install --no-cache-dir typing-extensions
sleep 2

echo ""
echo "Step 3: Installing pydantic-core..."
python -m pip install --no-cache-dir pydantic-core
sleep 2

echo ""
echo "Step 4: Installing pydantic..."
python -m pip install --no-cache-dir pydantic
sleep 2

echo ""
echo "Step 5: Installing tqdm..."
python -m pip install --no-cache-dir tqdm
sleep 2

echo ""
echo "Step 6: Installing requests (already have it)..."
python -m pip install --no-cache-dir requests
sleep 2

echo ""
echo "Step 7: Installing googleapis-common-protos..."
python -m pip install --no-cache-dir googleapis-common-protos
sleep 2

echo ""
echo "Step 8: Installing proto-plus..."
python -m pip install --no-cache-dir proto-plus
sleep 2

echo ""
echo "Step 9: Installing google-auth..."
python -m pip install --no-cache-dir google-auth
sleep 2

echo ""
echo "Step 10: Installing google-api-core (without grpc)..."
python -m pip install --no-cache-dir google-api-core
sleep 2

echo ""
echo "Step 11: Installing google-ai-generativelanguage..."
python -m pip install --no-cache-dir google-ai-generativelanguage
sleep 2

echo ""
echo "Step 12: Installing google-api-python-client..."
python -m pip install --no-cache-dir google-api-python-client
sleep 2

echo ""
echo "Step 13: Installing google-generativeai (main package)..."
python -m pip install --no-cache-dir --no-deps google-generativeai
sleep 2

echo ""
echo "=================================================="
echo "Testing imports..."
echo "=================================================="
python3 -c "import google.generativeai; import PIL; print('✅ Everything working!')"

echo ""
echo "=================================================="
echo "✅ Installation complete!"
echo "=================================================="
echo ""
echo "Now restart your bot:"
echo "sudo systemctl restart vega-queue"
