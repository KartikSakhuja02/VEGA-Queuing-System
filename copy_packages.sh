#!/bin/bash
# Copy ALL packages from any working venv on this machine into this project's venv.
# Run this script from ANYWHERE — it figures out all paths automatically.

set -e

echo "=================================================="
echo "  VEGA Queue System — Venv Package Copier"
echo "=================================================="
echo ""

# ── 1. Find THIS project's directory (the folder containing this script) ──
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_VENV="$SCRIPT_DIR/venv"

echo "Project dir  : $SCRIPT_DIR"
echo "Target venv  : $TARGET_VENV"
echo ""

# ── 2. Create fresh venv if it doesn't exist yet ──
if [ ! -f "$TARGET_VENV/bin/python" ]; then
    echo "Creating new venv at $TARGET_VENV ..."
    python3 -m venv "$TARGET_VENV"
    echo "✅ Venv created"
else
    echo "✅ Venv already exists"
fi
echo ""

# ── 3. Auto-discover a working source venv ──
CANDIDATE_VENVS=(
    "$HOME/Documents/Valorant-Mobile-India-Queue/venv"
    "$HOME/Documents/Valorant-Mobile-Tournament/venv"
    "$HOME/Documents/Valorant-Tournament/venv"
    "$HOME/Documents/Valm-India-Queue/venv"
    "$HOME/Documents/valmindiaqueue/venv"
    "$HOME/venv"
)

SOURCE_VENV=""
for CANDIDATE in "${CANDIDATE_VENVS[@]}"; do
    if [ -d "$CANDIDATE/lib" ] && ls "$CANDIDATE/lib/python3."*/site-packages/discord 1>/dev/null 2>&1; then
        SOURCE_VENV="$CANDIDATE"
        break
    fi
done

# Fallback: scan ~/Documents for any venv with discord installed
if [ -z "$SOURCE_VENV" ]; then
    while IFS= read -r cfg; do
        DIR="$(dirname "$(dirname "$cfg")")"
        if ls "$DIR/lib/python3."*/site-packages/discord 1>/dev/null 2>&1; then
            SOURCE_VENV="$DIR"
            break
        fi
    done < <(find "$HOME/Documents" -maxdepth 4 -name "pyvenv.cfg" 2>/dev/null)
fi

if [ -z "$SOURCE_VENV" ]; then
    echo "❌  Could not find any venv with discord.py installed."
    echo "   Run:  find ~/Documents -maxdepth 4 -name pyvenv.cfg"
    echo "   Then re-run this script from that venv's parent directory."
    exit 1
fi

echo "Source venv  : $SOURCE_VENV"
echo ""

# ── 4. Locate site-packages in both venvs ──
SOURCE_SITE=$(find "$SOURCE_VENV/lib" -type d -name "site-packages" | head -n 1)
TARGET_SITE=$(find "$TARGET_VENV/lib" -type d -name "site-packages" | head -n 1)

echo "Copying packages..."
echo "From: $SOURCE_SITE"
echo "To:   $TARGET_SITE"
echo ""

# ── 5. Copy EVERYTHING from source site-packages ──
# rsync preferred (preserves symlinks, skips identical files), cp as fallback
if command -v rsync &>/dev/null; then
    rsync -a --info=progress2 "$SOURCE_SITE/" "$TARGET_SITE/"
else
    cp -r "$SOURCE_SITE/." "$TARGET_SITE/"
fi

echo ""
echo "=================================================="
echo "✅ Packages copied successfully!"
echo "=================================================="
echo ""
echo "Testing imports..."
cd "$SCRIPT_DIR"
source venv/bin/activate
if python -c "import discord, asyncpg, dotenv, google.generativeai, PIL; print('✅ All imports working!')" 2>&1; then
    echo ""
    echo "=================================================="
    echo " Bot is ready! To start the service run:"
    echo "   sudo systemctl restart vega-queue.service"
    echo " Or test manually first:"
    echo "   source venv/bin/activate && python bot.py"
    echo "=================================================="
else
    echo ""
    echo "Some imports failed — run:  pip list | grep -i <package>"
    echo "then install any missing ones manually."
fi

