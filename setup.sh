#!/usr/bin/env bash
set -euo pipefail

echo "==> Installing Winecellar (user install, no venv)"

# 1. Ensure Python & pip
command -v python3 >/dev/null || {
    echo "ERROR: python3 not found"
    exit 1
}

command -v pip >/dev/null || {
    echo "ERROR: pip not found"
    exit 1
}

# 2. Install Winecellar
pip install --user --upgrade .

# 3. Ensure ~/.local/bin is on PATH
if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
    echo "==> Adding ~/.local/bin to PATH"
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
    export PATH="$HOME/.local/bin:$PATH"
fi

# 4. Ensure Bottles global config exists
BOTTLES_CFG="$HOME/.local/share/bottles"
mkdir -p "$BOTTLES_CFG"

if [ ! -f "$BOTTLES_CFG/config.yml" ]; then
    echo "==> Creating Bottles global config.yml"
    touch "$BOTTLES_CFG/config.yml"
fi

# 5. Verify install
echo "==> Verifying installation"
command -v winecellar >/dev/null || {
    echo "ERROR: winecellar not found on PATH"
    exit 1
}

winecellar --help >/dev/null

echo
echo "✅ Winecellar installed successfully"
echo
echo "You can now run:"
echo "  winecellar update -c ./windows32.yml"
echo "to create a new bottle with a predefined configuration."