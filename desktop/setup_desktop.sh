#!/bin/bash
# ──────────────────────────────────────────────────────────────────────────
#  Mimo Desktop Setup Script
#  Run once after installing the base requirements:
#    pip install -r requirements.txt
#    chmod +x desktop/setup_desktop.sh
#    ./desktop/setup_desktop.sh
# ──────────────────────────────────────────────────────────────────────────

set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}  ✓  $*${NC}"; }
warn() { echo -e "${YELLOW}  ⚠  $*${NC}"; }
fail() { echo -e "${RED}  ✗  $*${NC}"; }

echo ""
echo "──────────────────────────────────────────────────────"
echo "  Mimo Desktop App — Dependency Setup"
echo "──────────────────────────────────────────────────────"
echo ""

OS=$(uname -s)
PYTHON=$(which python3 || which python)

# ── Python check ──────────────────────────────────────────────────────────
PY_VER=$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
ok "Python $PY_VER"

# ── pip install desktop packages ──────────────────────────────────────────
echo ""
echo "Installing desktop packages..."
$PYTHON -m pip install -r requirements_desktop.txt -q
ok "Desktop Python packages installed"

# ── OS-specific system packages ───────────────────────────────────────────
echo ""
echo "Checking OS-specific requirements..."

if [ "$OS" = "Linux" ]; then
    # pystray on Linux needs GTK3 and AppIndicator
    if command -v apt-get &>/dev/null; then
        echo "Installing GTK + AppIndicator (Ubuntu/Debian)..."
        sudo apt-get install -y -q \
            python3-gi \
            python3-gi-cairo \
            gir1.2-gtk-3.0 \
            gir1.2-appindicator3-0.1 \
            libappindicator3-dev \
            libnotify-bin \
            xdotool 2>/dev/null || warn "Some packages failed — tray may not work"
        ok "GTK + AppIndicator installed"
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y -q \
            python3-gobject \
            gtk3 \
            libappindicator-gtk3 \
            libnotify \
            xdotool 2>/dev/null || warn "Some packages failed"
        ok "GTK packages installed (Fedora)"
    else
        warn "Unknown Linux distro — install GTK3, AppIndicator, and libnotify manually."
    fi

elif [ "$OS" = "Darwin" ]; then
    # macOS: check for pywebview dependencies
    if command -v brew &>/dev/null; then
        brew install --quiet python-tk 2>/dev/null || true
        ok "macOS dependencies checked"
    else
        warn "Homebrew not found — install python-tk manually if splash screen fails."
    fi

elif [[ "$OS" == MINGW* ]] || [[ "$OS" == CYGWIN* ]] || [[ "$OS" == MSYS* ]]; then
    # Windows: usually works out of the box
    ok "Windows detected — no extra system packages needed"
fi

# ── Pre-generate tray icons ───────────────────────────────────────────────
echo ""
echo "Generating tray icons..."
$PYTHON -c "
from desktop.icon_generator import save_icon
for state in ('active','paused','alert'):
    save_icon(state, 64)
    save_icon(state, 32)
print('Icons generated in desktop/assets/')
" && ok "Tray icons ready"

# ── Check .env ────────────────────────────────────────────────────────────
echo ""
if [ ! -f ".env" ]; then
    cp .env.example .env
    warn ".env created from template. Edit it and add your OPENAI_API_KEY."
else
    ok ".env already exists"
fi

# ── Done ──────────────────────────────────────────────────────────────────
echo ""
echo "──────────────────────────────────────────────────────"
ok "Desktop setup complete!"
echo ""
echo "  To launch Mimo as a desktop app:"
echo "    python run_desktop.py"
echo ""
echo "  To build a distributable .exe/.app:"
echo "    python desktop/build.py"
echo ""
