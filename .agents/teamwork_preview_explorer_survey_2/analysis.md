# PyInstaller Build Requirements & Hazard Analysis (Requirement R2)

## 1. Executive Summary

This report provides a comprehensive read-only investigation of Requirement R2 (Compile Final Desktop App) for the Mimo cross-platform application. The goal of Requirement R2 is to compile the final `Mimo.exe` Desktop app using PyInstaller, ensure the `static/` directory is correctly bundled, and verify clean startup and shutdown without zombie background process hanging.

### Summary of Key Findings
1. **Desktop App Architecture**: Located in `desktop/` directory with entry point `desktop/main_desktop.py` (wrapped by root `run_desktop.py`).
2. **Static Bundling Mechanics**: `static/` directory (containing `dashboard.html`, `schedule.html`, `settings.html`, `parent_portal.html`, `file_tree.html`) is correctly referenced in spec files (`datas=[(ROOT/static, static)]`). `desktop/main_desktop.py` changes the working directory to `sys._MEIPASS` when frozen, allowing relative backend routes (`StaticFiles(directory="static")`) to resolve correctly.
3. **PyInstaller Spec File Inconsistency**:
   - There are **three different build definitions**: `desktop/mimo.spec` (comprehensive), `Mimo.spec` (incomplete root spec), and `desktop/build.py` (incomplete CLI wrapper).
   - `Mimo.spec` and `desktop/build.py` lack critical hidden imports (`fastapi`, `starlette`, `sqlalchemy`, `pystray`, `webview`, `plyer`, `apscheduler`), which will cause a startup crash (`ModuleNotFoundError`) if used.
   - `desktop/mimo.spec` includes full hidden imports, but line 126 explicitly excludes `"numpy"`, which causes a `ModuleNotFoundError` because `modules/cv_pipeline/focus_detector.py`, `presence.py`, and `stream_client.py` import `numpy`.
4. **Zombie Process & Launch Hazards**:
   - **Main Thread Sleeping Loop**: In `desktop/main_desktop.py` (lines 327–333), after `webview.start()` finishes or falls back to browser, the main thread enters `while True: time.sleep(1)`. In `--noconsole` mode, Ctrl+C cannot interrupt it. If the system tray fails or is closed without quit action, the process becomes an invisible zombie.
   - **Abrupt `os._exit(0)` in System Tray Quit**: `desktop/tray.py` line 201 terminates the application via `os._exit(0)`, bypassing `atexit` cleanup routines (`_shutdown()`, `_release_lock()`, `stop_all()`).

---

## 2. Desktop App Source Architecture & Entry Points

### 2.1 File Map

| Component | File Path | Purpose |
| --- | --- | --- |
| **Root Launcher** | `run_desktop.py` | Sets `sys.path` and invokes `desktop.main_desktop.main()`. |
| **Main Desktop Entry** | `desktop/main_desktop.py` | Initializes logging, single instance guard, splash screen, FastAPI background server, pywebview GUI window, system tray, and main event loop. |
| **Window Manager** | `desktop/window_manager.py` | Wraps pywebview lifecycle, handles window hide on close (`X`), focus, and fallback to default browser. |
| **System Tray** | `desktop/tray.py` | Manages `pystray` icon, live stats refresh loop, popup menu actions (Pause, Settings, Autostart, Quit). |
| **Splash Screen** | `desktop/splash.py` | Tkinter-based splash screen displayed during server startup. |
| **Single Instance Guard** | `desktop/single_instance.py` | Windows Mutex (`CreateMutexW`) / Unix PID lock file (`~/.mimo/mimo.pid`) to prevent duplicate app instances. |
| **Autostart Guard** | `desktop/autostart.py` | Windows Registry (`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`) auto-start manager. |
| **Notifications** | `desktop/notifications.py` | Plyer wrapper for native OS desktop notifications. |
| **Icon Generator** | `desktop/icon_generator.py` | Pillow-based dynamic tray icon generator (draws flame icon for active/paused/alert states). |

### 2.2 Spec Files and Build Scripts

The repository contains **three competing PyInstaller build definitions**:

```
Mimo/
├── Mimo.spec                 # Root spec file (Incomplete hidden imports)
└── desktop/
    ├── mimo.spec             # Comprehensive spec file (Primary target)
    └── build.py              # CLI build script wrapper (Incomplete hidden imports)
```

#### Detailed Comparison Matrix:

| Feature | `desktop/mimo.spec` | `Mimo.spec` (Root) | `desktop/build.py` |
| --- | --- | --- | --- |
| **Script Entry Point** | `desktop/main_desktop.py` | `run_desktop.py` | `run_desktop.py` |
| **Target Output Name** | `Mimo` (`dist/Mimo/Mimo.exe`) | `Mimo` (`dist/Mimo/Mimo.exe`) | `Mimo` (`dist/Mimo/Mimo.exe`) |
| **Console Window** | `console=False` | `console=False` | `--noconsole` |
| **Bundled Data Directories** | `static/`, `desktop/assets/`, `.env.example`, `README.md` | `static/`, `assets/` | `static/`, `assets/` |
| **Icon File** | `desktop/assets/mimo_active_64.png` | `assets\app_icon.ico` | `assets/app_icon.ico` |
| **Hidden Imports** | Comprehensive (40+ modules including FastAPI, SQLAlchemy, pystray, pywebview, plyer, APScheduler) | Incomplete (uvicorn, websockets, psutil, sqlite3, pydantic) | Incomplete (uvicorn, websockets, psutil, sqlite3, pydantic) |
| **Excludes** | `['pytest', 'IPython', 'jupyter', 'matplotlib', 'pandas', 'numpy']` | None | None |

---

## 3. Static Directory (`static/`) Bundling & Path Resolution Analysis

### 3.1 Static Directory Contents
The `static/` directory contains 5 frontend HTML SPA documents:
- `static/dashboard.html` (92.8 KB — main SPA dashboard)
- `static/schedule.html` (11.8 KB — schedule manager)
- `static/settings.html` (10.4 KB — settings panel)
- `static/parent_portal.html` (22.2 KB — parent oversight portal)
- `static/file_tree.html` (20.5 KB — file explorer view)

### 3.2 PyInstaller Data Configuration
In `desktop/mimo.spec` lines 98–107:
```python
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(SPEC)))

datas = [
    (os.path.join(ROOT, "static"),         "static"),
    (os.path.join(ROOT, "desktop", "assets"), os.path.join("desktop", "assets")),
    (os.path.join(ROOT, ".env.example"),   "."),
    (os.path.join(ROOT, "README.md"),      "."),
]
```
When compiled with PyInstaller in `--onedir` mode (COLLECT), PyInstaller outputs the contents of `static/` into `dist/Mimo/_internal/static` (PyInstaller v6+) or `dist/Mimo/static`.

### 3.3 Runtime Working Directory Resolution (`sys._MEIPASS`)
When running as a PyInstaller executable (`getattr(sys, "frozen", False) == True`), PyInstaller sets `sys._MEIPASS` to point to the directory where data files are bundled (`dist/Mimo/_internal`).

In `desktop/main_desktop.py` lines 39–43:
```python
if getattr(sys, "frozen", False):
    if hasattr(sys, "_MEIPASS"):
        os.chdir(sys._MEIPASS)
```
Because `os.chdir(sys._MEIPASS)` changes the process's working directory to `sys._MEIPASS` at startup:
1. **FastAPI Static File Mounting** (`main.py` line 90):
   ```python
   app.mount("/static", StaticFiles(directory="static"), name="static")
   ```
   Resolves relative path `static` to `sys._MEIPASS/static`.
2. **HTML Response Routes** (`main.py` lines 176, 181, 186):
   ```python
   FileResponse("static/dashboard.html")
   FileResponse("static/schedule.html")
   FileResponse("static/parent_portal.html")
   ```
   All resolve relative paths to `sys._MEIPASS/static/...`.
3. **Settings Route** (`api/routes_settings.py` lines 33–36):
   ```python
   path = os.path.join(
       os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
       "static", "settings.html",
   )
   ```
   In a bundled app, `__file__` inside `api/routes_settings.py` is `sys._MEIPASS/api/routes_settings.pyc`. Parent of parent is `sys._MEIPASS`, so `os.path.join(sys._MEIPASS, "static", "settings.html")` correctly locates `settings.html`.

**Verdict on `static/` bundling**: The configuration in `desktop/mimo.spec` correctly packages `static/`, and the runtime path resolution works seamlessly provided `desktop/mimo.spec` is used.

---

## 4. Dependencies, Build Commands, and Spec File Defects

### 4.1 Required Dependencies
- **Core Requirements** (`requirements.txt`): `fastapi`, `uvicorn[standard]`, `websockets`, `python-multipart`, `sqlalchemy`, `aiosqlite`, `alembic`, `pydantic`, `python-dotenv`, `psutil`, `pygetwindow`, `opencv-python`, `mediapipe`, `SpeechRecognition`, `pyttsx3`, `pyaudio`, `openai`, `google-genai`, `python-jose`, `bcrypt`, `apscheduler`, `dateparser`, `python-dateutil`, `httpx`, `aiofiles`.
- **Desktop Requirements** (`requirements_desktop.txt`): `pystray==0.19.5`, `Pillow==10.3.0`, `pywebview==5.1`, `plyer==2.1.0`, `pyinstaller==6.8.0`.

### 4.2 Target Output Path
The output directory defined in all spec files (`COLLECT(..., name='Mimo')`) is:
```
dist/Mimo/
├── Mimo.exe
└── _internal/
    ├── static/
    ├── desktop/assets/
    └── [DLLs, .pyd binary extensions, Python standard library]
```

### 4.3 Defects Identified in Build Definitions

#### Defect 1: Incomplete Hidden Imports in `Mimo.spec` & `desktop/build.py`
Both root `Mimo.spec` and `desktop/build.py` omit essential imports needed by FastAPI, SQLAlchemy, PyStray, PyWebview, and Plyer. If built using `Mimo.spec` or `desktop/build.py`, the executable crashes immediately upon launch with:
```
ModuleNotFoundError: No module named 'fastapi'
```

#### Defect 2: Conflict with Excluded `"numpy"` in `desktop/mimo.spec`
In `desktop/mimo.spec` line 126:
```python
    excludes          = [
        "pytest",
        "IPython",
        "jupyter",
        "matplotlib",
        "pandas",
        "numpy",    # ONLY exclude if not used!
    ],
```
However, direct `grep` analysis of the project source code reveals:
- `modules/cv_pipeline/focus_detector.py` line 25: `import numpy as np`
- `modules/cv_pipeline/presence.py` line 20: `import numpy as np`
- `modules/cv_pipeline/stream_client.py` line 13: `import numpy as np`

Because `numpy` is explicitly imported by computer vision modules, keeping `"numpy"` in `excludes` in `desktop/mimo.spec` causes a `ModuleNotFoundError: No module named 'numpy'` whenever `modules/cv_pipeline` is loaded.

---

## 5. Zombie Process Hazards & Launch Lifecycle Analysis

### 5.1 Main Thread Endless Sleep Loop
In `desktop/main_desktop.py` lines 302–333:
```python
if webview_ok:
    try:
        import webview
        webview.start(func=wm.on_webview_start, debug=False, private_mode=False)
        log.info("pywebview event loop ended — app running in system tray.")
    except Exception as e:
        _open_browser_fallback()
else:
    _open_browser_fallback()

# ── keep main thread alive while tray is running ──────────────────────
log.info("App running in system tray. Press Ctrl+C to quit.")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    log.info("Keyboard interrupt — shutting down.")
    _shutdown(wm)
    sys.exit(0)
```

#### Hazard Mechanics:
1. **No Console Window**: The PyInstaller build config sets `console=False` (`--noconsole`). Under Windows non-console executables, standard streams (stdin/stdout) are detached, and keyboard signals like `Ctrl+C` cannot be sent or received.
2. **Hanging Condition**: Once `webview.start()` returns (e.g. when the user closes the pywebview window, or if pywebview fails and opens the default browser instead), main execution enters `while True: time.sleep(1)`.
3. **Zombie Hazard**: If `pystray` system tray fails to initialize (or if the user closes the browser tab/window without using the system tray Quit option), the process stays stuck in the `while True` loop indefinitely. The background FastAPI server and background scheduler threads keep running silently, consuming system RAM/CPU with no UI and no tray icon.

### 5.2 Abrupt Process Exit via `os._exit(0)`
In `desktop/tray.py` lines 196–201:
```python
def _on_quit(self, icon=None, item=None):
    log.info("Quit requested from tray.")
    if self._icon:
        self._icon.stop()
    import os
    os._exit(0)
```

#### Hazard Mechanics:
1. `os._exit(0)` instantly exits the process at the C process level without unwinding the stack or calling Python cleanup routines.
2. **Bypassed Handlers**:
   - `atexit.register(_shutdown, wm)` in `main_desktop.py` is **BYPASSED**.
   - `atexit.register(_release_lock)` in `main_desktop.py` is **BYPASSED**.
   - `stop_all()` in `schedulers/background_tasks.py` (which stops screen tracker, voice listener, presence monitor) is **NEVER CALLED**.
   - `stop_scheduler()` in `schedulers/daily_trigger.py` is **NEVER CALLED**.
3. **Impact**:
   - Screen tracker fails to flush final active session to SQLite database.
   - Single-instance lock file/handle cleanup relies entirely on OS kernel process drop rather than application-level release.

### 5.3 Missing `CREATE_NO_WINDOW` Flag in Subprocess Execution
In `modules/screen_tracker/tracker.py` lines 228–232:
```python
if _SYSTEM == "Windows":
    import subprocess
    subprocess.run(["taskkill", "/F", "/IM", f"{app_name}.exe"], capture_output=True)
```
When running inside a `--noconsole` executable on Windows, calling `subprocess.run` without specifying `creationflags=subprocess.CREATE_NO_WINDOW` (or `0x08000000`) can spawn brief transient console windows or background subprocess handles.

---

## 6. Recommendations & Action Plan for Implementation

To satisfy Requirement R2 and produce a clean, working PyInstaller executable:

1. **Use `desktop/mimo.spec` as the Single Source of Truth**:
   - Remove or deprecate `Mimo.spec` and `desktop/build.py` to prevent accidental builds with incomplete hidden imports.
   - Execute PyInstaller using:
     ```powershell
     pyinstaller desktop/mimo.spec
     ```
2. **Fix `numpy` Exclusion in `desktop/mimo.spec`**:
   - Remove `"numpy"` from `excludes` in `desktop/mimo.spec` line 126.
3. **Refactor Main Thread Sleep Loop in `desktop/main_desktop.py`**:
   - Link main thread lifecycle to system tray or pywebview state, ensuring that when the app is shut down or system tray quits, the main loop exits cleanly (`sys.exit(0)`).
4. **Replace `os._exit(0)` with Clean Shutdown**:
   - Update `_on_quit` in `desktop/tray.py` to call `_shutdown(wm)` before exiting, ensuring `stop_all()`, `stop_scheduler()`, and single instance lock release execute properly.
5. **Add `CREATE_NO_WINDOW` Flag to Subprocess Calls**:
   - Ensure all `subprocess.run` calls in Windows desktop modules pass `creationflags=subprocess.CREATE_NO_WINDOW`.

---
*Report compiled by teamwork_preview_explorer_survey_2 for Requirement R2 PyInstaller Investigation.*
