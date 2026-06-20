"""
desktop/build.py — Mimo desktop app build script.

Runs PyInstaller with the mimo.spec and produces the distributable app.

Usage:
    python desktop/build.py               # full build
    python desktop/build.py --clean       # wipe dist/ first
    python desktop/build.py --check-only  # only run pre-flight checks

Output:
    dist/Mimo/         ← Windows/Linux: folder with Mimo.exe / Mimo
    dist/Mimo.app/     ← macOS: .app bundle (zip for distribution)
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys

ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC     = os.path.join(ROOT, "desktop", "mimo.spec")
DIST_DIR = os.path.join(ROOT, "dist")
BUILD_DIR = os.path.join(ROOT, "build")

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
RESET  = "\033[0m"

def ok(msg):    print(f"{GREEN}  ✓  {msg}{RESET}")
def warn(msg):  print(f"{YELLOW}  ⚠  {msg}{RESET}")
def fail(msg):  print(f"{RED}  ✗  {msg}{RESET}")
def info(msg):  print(f"     {msg}")


# ── Pre-flight checks ──────────────────────────────────────────────────────

def check_python() -> bool:
    v = sys.version_info
    if v.major == 3 and v.minor >= 10:
        ok(f"Python {v.major}.{v.minor}.{v.micro}")
        return True
    fail(f"Python 3.10+ required. Got {v.major}.{v.minor}")
    return False


def check_pyinstaller() -> bool:
    try:
        import PyInstaller
        ok(f"PyInstaller {PyInstaller.__version__}")
        return True
    except ImportError:
        warn("PyInstaller not installed. Installing now...")
        code = subprocess.call([sys.executable, "-m", "pip", "install", "pyinstaller>=6.0"])
        if code == 0:
            ok("PyInstaller installed.")
            return True
        fail("PyInstaller install failed. Run: pip install pyinstaller")
        return False


def check_requirements() -> bool:
    missing = []
    for pkg in ("pystray", "PIL", "plyer", "webview", "httpx"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if missing:
        warn(f"Missing desktop packages: {', '.join(missing)}")
        info("Install with: pip install -r requirements_desktop.txt")
        return False
    ok("All desktop requirements present.")
    return True


def check_env() -> bool:
    env_path = os.path.join(ROOT, ".env")
    if os.path.exists(env_path):
        ok(".env file found.")
        return True
    warn(".env file missing.")
    info("Copy .env.example to .env and add your OPENAI_API_KEY before running.")
    return True   # Non-fatal — user can add it after install


def check_icons() -> bool:
    icon_path = os.path.join(ROOT, "desktop", "assets", "mimo_active_64.png")
    if os.path.exists(icon_path):
        ok("Tray icons present.")
        return True
    info("Generating tray icons...")
    try:
        sys.path.insert(0, ROOT)
        from desktop.icon_generator import save_icon
        for state in ("active", "paused", "alert"):
            save_icon(state)
        ok("Tray icons generated.")
        return True
    except Exception as e:
        warn(f"Icon generation failed: {e}")
        return True   # Non-fatal — PyInstaller will just skip the icon


def run_checks() -> bool:
    print("\n── Pre-flight checks ────────────────────────────────────")
    checks = [
        check_python(),
        check_pyinstaller(),
        check_requirements(),
        check_env(),
        check_icons(),
    ]
    print()
    if all(checks):
        ok("All checks passed. Ready to build.\n")
        return True
    fail("Some checks failed. Fix them and retry.\n")
    return False


# ── Build ──────────────────────────────────────────────────────────────────

def clean_dist():
    for d in (DIST_DIR, BUILD_DIR):
        if os.path.exists(d):
            shutil.rmtree(d)
            ok(f"Cleaned {d}")


def build() -> int:
    print("── Building Mimo ─────────────────────────────────────────")
    info(f"Platform : {platform.system()} {platform.machine()}")
    info(f"Python   : {sys.version.split()[0]}")
    info(f"Spec     : {SPEC}")
    info(f"Output   : {DIST_DIR}/Mimo")
    print()

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--log-level", "WARN",
        SPEC,
    ]

    print(f"Running: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=ROOT)
    return result.returncode


def post_build():
    """Copy .env.example to dist so users know they need a .env."""
    src  = os.path.join(ROOT, ".env.example")
    dst  = os.path.join(DIST_DIR, "Mimo", ".env.example")
    if os.path.exists(src):
        shutil.copy2(src, dst)
        ok("Copied .env.example to dist/Mimo/")

    # Print instructions
    print()
    print("── Build complete ────────────────────────────────────────")
    ok(f"App is in: dist/Mimo/")
    print()
    info("To run the built app:")
    if platform.system() == "Windows":
        info("  dist\\Mimo\\Mimo.exe")
    elif platform.system() == "Darwin":
        info("  open dist/Mimo.app")
        info("  (or right-click → Open if macOS blocks it)")
    else:
        info("  ./dist/Mimo/Mimo")
    print()
    info("Before first run, create dist/Mimo/.env from .env.example")
    info("and set OPENAI_API_KEY.")
    print()


# ── macOS: zip the .app for sharing ───────────────────────────────────────

def zip_macos_app():
    if platform.system() != "Darwin":
        return
    app_path = os.path.join(DIST_DIR, "Mimo.app")
    zip_path = os.path.join(DIST_DIR, "Mimo_macOS.zip")
    if os.path.exists(app_path):
        info("Zipping macOS .app for distribution...")
        shutil.make_archive(
            os.path.join(DIST_DIR, "Mimo_macOS"),
            "zip",
            DIST_DIR,
            "Mimo.app",
        )
        ok(f"Zipped: {zip_path}")


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Build the Mimo desktop app.")
    parser.add_argument("--clean",      action="store_true", help="Clean dist/ before build")
    parser.add_argument("--check-only", action="store_true", help="Only run pre-flight checks")
    args = parser.parse_args()

    if args.clean:
        clean_dist()

    if not run_checks():
        sys.exit(1)

    if args.check_only:
        info("Check-only mode — skipping build.")
        sys.exit(0)

    rc = build()
    if rc != 0:
        fail(f"PyInstaller exited with code {rc}.")
        sys.exit(rc)

    post_build()
    zip_macos_app()


if __name__ == "__main__":
    main()
