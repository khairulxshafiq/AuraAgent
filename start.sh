#!/bin/bash
# ─── AURA SDK — Local Startup Script ─────────────────────────────────────────
# Run this to start AURA locally.
# Double-click atau run: bash start.sh

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo ""
echo "========================================="
echo "    AURA SDK — Personal AI OS"
echo "    Starting local bot..."
echo "========================================="
echo ""

# Check .env
if [ ! -f ".env" ]; then
    echo "❌ ERROR: .env file not found!"
    echo "   Copy .env.example to .env and fill in your keys."
    exit 1
fi

# Setup virtual environment
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

echo "🔄 Activating virtual environment..."
source .venv/bin/activate

echo "📦 Installing dependencies..."
pip install -q -r requirements.txt

echo ""
echo "✅ AURA is starting!"
echo "   Open Telegram and send /start to your bot."
echo "   Press Ctrl+C to stop."
echo ""

python main.py
