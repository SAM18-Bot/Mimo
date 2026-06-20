#!/bin/bash
# ─────────────────────────────────────────────────────────────────
#  Student AI Accountability System — Setup Script
#  Run once: chmod +x setup.sh && ./setup.sh
# ─────────────────────────────────────────────────────────────────

set -e
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

info "======================================================"
info "  AI Accountability System — Environment Setup"
info "======================================================"

# ── Python version check ──────────────────────────────────────
PYTHON=$(which python3 || which python)
PY_VERSION=$($PYTHON -c 'import sys; print(sys.version_info.major, sys.version_info.minor)')
PY_MAJOR=$(echo $PY_VERSION | cut -d' ' -f1)
PY_MINOR=$(echo $PY_VERSION | cut -d' ' -f2)

if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]); then
  error "Python 3.10+ is required. Found: $($PYTHON --version)"
  exit 1
fi
info "Python OK: $($PYTHON --version)"

# ── virtual environment ───────────────────────────────────────
if [ ! -d ".venv" ]; then
  info "Creating virtual environment..."
  $PYTHON -m venv .venv
fi

source .venv/bin/activate
info "Virtual environment active."

# ── pip install ───────────────────────────────────────────────
info "Installing dependencies..."
pip install --upgrade pip -q

# Core install
pip install -r requirements.txt -q

# Platform-specific installs
OS=$(uname -s)

if [ "$OS" = "Linux" ]; then
  info "Linux detected — installing xdotool (for screen tracking)..."
  if command -v apt-get &>/dev/null; then
    sudo apt-get install -y xdotool espeak portaudio19-dev -q 2>/dev/null || warn "apt-get failed — install xdotool, espeak, portaudio19-dev manually"
  elif command -v dnf &>/dev/null; then
    sudo dnf install -y xdotool espeak portaudio-devel -q 2>/dev/null || warn "dnf failed"
  fi
  # Use ewmh instead of pygetwindow on Linux
  pip install ewmh -q 2>/dev/null || warn "ewmh install failed — screen tracking may be limited"

elif [ "$OS" = "Darwin" ]; then
  info "macOS detected."
  if command -v brew &>/dev/null; then
    brew install portaudio -q 2>/dev/null || warn "brew portaudio failed — install manually"
  fi

elif [[ "$OS" == MINGW* ]] || [[ "$OS" == CYGWIN* ]] || [[ "$OS" == MSYS* ]]; then
  info "Windows detected."
  pip install pywin32 pygetwindow -q || warn "pywin32 install failed"
fi

# ── .env setup ────────────────────────────────────────────────
if [ ! -f ".env" ]; then
  cp .env.example .env
  warn ".env created from template. EDIT IT NOW:"
  warn "  1. Add your OPENAI_API_KEY"
  warn "  2. Set ESP32_STREAM_URL to your ESP32-CAM IP"
  echo ""
  info "Opening .env for editing (Ctrl+C to skip)..."
  sleep 2
  ${EDITOR:-nano} .env || true
else
  info ".env already exists."
fi

# ── DB init check ─────────────────────────────────────────────
info "Initializing database..."
$PYTHON -c "from db.database import init_db; init_db(); print('DB OK')"

# ── done ─────────────────────────────────────────────────────
echo ""
info "======================================================"
info "  Setup complete!"
info "======================================================"
echo ""
echo "  To run the system:"
echo "  source .venv/bin/activate"
echo "  uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
echo ""
echo "  Dashboard: http://localhost:8000"
echo "  API docs:  http://localhost:8000/docs"
echo ""
