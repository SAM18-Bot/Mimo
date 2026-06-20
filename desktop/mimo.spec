# -*- mode: python ; coding: utf-8 -*-
"""
Mimo PyInstaller Build Spec
─────────────────────────────
Produces a one-folder app bundle.

Build:
    pyinstaller desktop/mimo.spec

Output:
    dist/Mimo/             ← the folder to distribute
    dist/Mimo/Mimo         ← or Mimo.exe on Windows

Notes:
  - The .env file is NOT included — users must provide their own.
  - The static/ directory IS included (the web dashboard).
  - mediapipe and opencv binaries are collected automatically.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(SPEC)))

block_cipher = None

# ── Hidden imports ─────────────────────────────────────────────────────────
# FastAPI / uvicorn have many lazy-loaded modules PyInstaller misses.
hidden_imports = [
    # uvicorn
    "uvicorn",
    "uvicorn.main",
    "uvicorn.config",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.loops.uvloop",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.protocols.websockets.wsproto_impl",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    # FastAPI / Starlette
    "fastapi",
    "starlette",
    "starlette.middleware",
    "starlette.middleware.cors",
    "starlette.staticfiles",
    "starlette.responses",
    "starlette.websockets",
    # SQLAlchemy
    "sqlalchemy",
    "sqlalchemy.dialects",
    "sqlalchemy.dialects.sqlite",
    "sqlalchemy.dialects.sqlite.pysqlite",
    "sqlalchemy.orm",
    "sqlalchemy.ext.declarative",
    # Pydantic
    "pydantic",
    "pydantic.v1",
    # APScheduler
    "apscheduler",
    "apscheduler.schedulers",
    "apscheduler.schedulers.background",
    "apscheduler.triggers.cron",
    "apscheduler.triggers.interval",
    "apscheduler.executors.default",
    # dateparser
    "dateparser",
    "dateparser.search",
    # pywebview
    "webview",
    # pystray
    "pystray",
    # plyer
    "plyer",
    "plyer.platforms.win.notification",
    "plyer.platforms.macosx.notification",
    "plyer.platforms.linux.notification",
    # Python standard library lazy imports
    "sqlite3",
    "email.mime.multipart",
    "email.mime.text",
    "logging.handlers",
    "tkinter",
    "tkinter.messagebox",
]

# ── Data files to bundle ───────────────────────────────────────────────────
datas = [
    # Web dashboard and settings page
    (os.path.join(ROOT, "static"),         "static"),
    # Desktop assets (tray icons)
    (os.path.join(ROOT, "desktop", "assets"), os.path.join("desktop", "assets")),
    # .env example (users copy this to .env)
    (os.path.join(ROOT, ".env.example"),   "."),
    # README
    (os.path.join(ROOT, "README.md"),      "."),
]

# ── Analysis ───────────────────────────────────────────────────────────────
a = Analysis(
    [os.path.join(ROOT, "desktop", "main_desktop.py")],
    pathex            = [ROOT],
    binaries          = [],
    datas             = datas,
    hiddenimports     = hidden_imports,
    hookspath         = [],
    hooksconfig       = {},
    runtime_hooks     = [],
    excludes          = [
        # Exclude heavy test / dev deps
        "pytest",
        "IPython",
        "jupyter",
        "matplotlib",
        "pandas",
        "numpy",    # only exclude if you don't use it; keep if mediapipe needs it
    ],
    win_no_prefer_redirects  = False,
    win_private_assemblies   = False,
    cipher                   = block_cipher,
    noarchive                = False,
)

# ── PYZ ───────────────────────────────────────────────────────────────────
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── EXE ───────────────────────────────────────────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries = True,
    name             = "Mimo",
    debug            = False,
    bootloader_ignore_signals = False,
    strip            = False,
    upx              = True,
    console          = False,   # No terminal window
    disable_windowed_traceback = False,
    target_arch      = None,
    codesign_identity = None,
    entitlements_file = None,
    icon             = os.path.join(ROOT, "desktop", "assets", "mimo_active_64.png"),
)

# ── COLLECT (one-folder mode) ─────────────────────────────────────────────
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip    = False,
    upx      = True,
    upx_exclude = [],
    name     = "Mimo",
)

# ── macOS BUNDLE ──────────────────────────────────────────────────────────
# Only runs on macOS — creates a proper .app bundle
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name             = "Mimo.app",
        icon             = os.path.join(ROOT, "desktop", "assets", "mimo_active_64.png"),
        bundle_identifier = "com.mimo.app",
        info_plist        = {
            "LSUIElement":             True,   # hide from Dock (tray app)
            "NSHighResolutionCapable": True,
            "CFBundleDisplayName":     "Mimo",
            "CFBundleShortVersionString": "1.0.0",
            "NSCameraUsageDescription": "Mimo uses the camera for presence monitoring.",
            "NSMicrophoneUsageDescription": "Mimo uses the microphone for voice commands.",
        },
    )
