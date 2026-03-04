#!/usr/bin/env bash
# build_mac.sh — Build ContainerOptimizer.app for macOS
#
# Prerequisites:
#   pip install pyinstaller
#   pip install -r requirements.txt   (WITHOUT gurobipy)
#
# Run from the project root:
#   chmod +x build_mac.sh
#   ./build_mac.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "=========================================="
echo " Container Optimizer — macOS Build"
echo "=========================================="
echo ""

# ── Sanity checks ─────────────────────────────────────────────────────────────
if ! command -v pyinstaller &>/dev/null; then
    echo "ERROR: pyinstaller not found. Run: pip install pyinstaller"
    exit 1
fi

if python -c "import gurobipy" 2>/dev/null; then
    echo "WARNING: gurobipy is installed in this environment."
    echo "         Build will proceed but CPMpy may try to import it at runtime."
    echo "         For a clean build, create a fresh venv without gurobipy."
    echo ""
fi

# ── Clean previous build ──────────────────────────────────────────────────────
echo "Cleaning previous build artifacts..."
rm -rf build/ dist/

# ── Build ─────────────────────────────────────────────────────────────────────
echo "Running PyInstaller..."
pyinstaller ContainerOptimizer.spec --noconfirm

# ── Copy user-editable config alongside the app ───────────────────────────────
DEST="dist/ContainerOptimizer.app/Contents/MacOS"
if [ -d "$DEST" ]; then
    echo "Copying optimizer_config.json alongside the app..."
    cp optimizer_config.json "$DEST/"
fi

# Also place it in dist/ root so users can find it easily
cp optimizer_config.json dist/

echo ""
echo "=========================================="
echo " Build complete!"
echo ""
echo " App bundle : dist/ContainerOptimizer.app"
echo " Config     : dist/ContainerOptimizer.app/Contents/MacOS/optimizer_config.json"
echo ""
echo " To run:    open dist/ContainerOptimizer.app"
echo " To ship:   zip -r ContainerOptimizer_mac.zip dist/ContainerOptimizer.app"
echo "            dist/optimizer_config.json"
echo "=========================================="
