#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$ROOT/.venv/bin/python"

if [[ ! -x "$PYTHON" ]]; then
    echo "Create the virtual environment first." >&2
    exit 1
fi

mkdir -p "$HOME/.local/share/applications"

cat > "$HOME/.local/share/applications/personal-finances.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Personal Finances
Comment=Local finance manager
Exec=$PYTHON $ROOT/desktop.py
Path=$ROOT
Terminal=false
Categories=Office;Finance;
StartupNotify=true
Icon=personal-finances
StartupWMClass=personal-finances
EOF

echo "Launcher installed."