#!/bin/bash
set -e

# Name of your virtual environment
VENV_DIR="$HOME/.winecellar-venv"

# Create the virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment at $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

# Activate the virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Upgrade pip, setuptools, wheel
pip install --upgrade pip setuptools wheel

# Install your package in the virtual environment
pip install --upgrade --quiet .

echo "Installation complete! To use Winecellar, activate the venv first:"
echo "  source $VENV_DIR/bin/activate"
echo "Then run: winecellar"

# Optional: Add a helper to ~/.bashrc for convenience
if ! grep -q "alias winecellar=" "$HOME/.bashrc"; then
    echo "Adding helper alias to ~/.bashrc"
    echo "alias winecellar='$VENV_DIR/bin/winecellar'" >> "$HOME/.bashrc"
    echo "You can now run 'winecellar' from any shell after restarting it."
fi
source "$HOME/.bashrc"
echo "Setup complete!"
