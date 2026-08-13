# Handoff Report — Requirement R2 PyInstaller Build Investigation

## 1. Observation

### 1.1 Source Code Architecture & Entry Points
- **Desktop Application Modules**: Located in `desktop/` (`main_desktop.py`, `window_manager.py`, `tray.py`, `splash.py`, `single_instance.py`, `autostart.py`, `notifications.py`, `icon_generator.py`).
- **Main Launcher**: `run_desktop.py` (lines 29–32) sets `sys.path` and executes `from desktop.main_desktop import main; main()`.
- **Main App Entry**: `desktop/main_desktop.py` (lines 250–356) handles single instance checks, splash screen, FastAPI background thread startup, pywebview creation, system tray initialization, and main loop.

### 1.2 Spec Files and Build Configurations
- **`desktop/mimo.spec`** (lines 110–166): Uses `os.path.join(ROOT, "desktop", "main_desktop.py")` as entry point. Specifies comprehensive `hidden_imports` (40+ modules including `uvicorn`, `fastapi`, `starlette`, `sqlalchemy`, `pydantic`, `apscheduler`, `dateparser`, `webview`, `pystray`, `plyer`).
- **`Mimo.spec` (Root)** (lines 4–16): Uses `run_desktop.py` as entry point. Contains an incomplete `hiddenimports` list (`['uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto', 'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto', 'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto', 'uvicorn.lifespan.on', 'uvicorn.lifespan.off', 'websockets', 'psutil', 'sqlite3', 'pydantic']`). Missing `fastapi`, `starlette`, `sqlalchemy`, `pystray`, `webview`, `plyer`, `apscheduler`.
- **`desktop/build.py`** (lines 11–37): Runs `sys.executable -m PyInstaller` with CLI arguments matching root `Mimo.spec`'s incomplete `--hidden-import` list.
- **`desktop/mimo.spec` Excludes List** (line 126): `excludes = ['pytest', 'IPython', 'jupyter', 'matplotlib', 'pandas', 'numpy']`.
- **Project Imports of `numpy`**:
  - `modules/cv_pipeline/focus_detector.py:25`: `import numpy as np`
  - `modules/cv_pipeline/presence.py:20`: `import numpy as np`
  - `modules/cv_pipeline/stream_client.py:13`: `import numpy as np`

### 1.3 Static Directory Bundling & Path Resolution
- **Static Directory**: `static/` contains `dashboard.html` (92.8 KB), `schedule.html` (11.8 KB), `settings.html` (10.4 KB), `parent_portal.html` (22.2 KB), and `file_tree.html` (20.5 KB).
- **Spec Data Configuration**: `desktop/mimo.spec` (line 100) bundles `(os.path.join(ROOT, "static"), "static")`.
- **Working Directory Override**: `desktop/main_desktop.py` (lines 39–43):
  ```python
  if getattr(sys, "frozen", False):
      if hasattr(sys, "_MEIPASS"):
          os.chdir(sys._MEIPASS)
  ```
- **Backend Routing**: `main.py` line 90: `app.mount("/static", StaticFiles(directory="static"), name="static")`; `main.py` lines 176, 181, 186 serve HTML files using `FileResponse("static/...")`. `api/routes_settings.py` line 33 accesses `os.path.join(..., "static", "settings.html")`.

### 1.4 Zombie Process & Lifecycle Hazards
- **Main Thread Sleeping Loop**: `desktop/main_desktop.py` lines 327–333:
  ```python
  log.info("App running in system tray. Press Ctrl+C to quit.")
  try:
      while True:
          time.sleep(1)
  except KeyboardInterrupt:
      ...
  ```
  In `--noconsole` mode on Windows, Ctrl+C signals cannot be delivered. If `pystray` tray fails to initialize or is closed without quit action, the process remains in an infinite sleep loop.
- **Abrupt Quit**: `desktop/tray.py` line 201: `_on_quit` executes `os._exit(0)`, bypassing `atexit.register(_shutdown, wm)` and `atexit.register(_release_lock)`.
- **Subprocess Creation**: `modules/screen_tracker/tracker.py` line 228 executes `subprocess.run(["taskkill", "/F", "/IM", ...])` without `creationflags=CREATE_NO_WINDOW`.

---

## 2. Logic Chain

1. **Observation 1.1 & 1.2** show that `desktop/mimo.spec` is the proper PyInstaller spec file containing the full set of required `hidden_imports`. Conversely, `Mimo.spec` (root) and `desktop/build.py` omit key packages such as `fastapi` and `pystray`. **Therefore**, building via `Mimo.spec` or `desktop/build.py` will produce an executable that crashes immediately with `ModuleNotFoundError`.
2. **Observation 1.2** shows that `desktop/mimo.spec` excludes `"numpy"`, while `modules/cv_pipeline/focus_detector.py`, `presence.py`, and `stream_client.py` explicitly `import numpy as np`. **Therefore**, building with `desktop/mimo.spec` as currently written will cause a runtime crash (`ModuleNotFoundError: No module named 'numpy'`) when CV modules are accessed.
3. **Observation 1.3** shows that `desktop/mimo.spec` bundles `static/` into `dist/Mimo/_internal/static`, and `desktop/main_desktop.py` changes the active directory to `sys._MEIPASS`. **Therefore**, relative static path resolutions in `main.py` (`StaticFiles(directory="static")` and `FileResponse("static/...")`) will correctly serve static HTML assets in the packaged executable.
4. **Observation 1.4** shows that in `desktop/main_desktop.py`, once `webview.start()` finishes, the main thread falls into `while True: time.sleep(1)`. Because `--noconsole` disables standard console signals, and `_on_quit` in `desktop/tray.py` executes `os._exit(0)` (bypassing `atexit` handlers), any failure in the system tray or close action without tray Quit will leave background daemon threads running permanently without an active UI, creating an invisible zombie process.

---

## 3. Caveats

1. **Read-Only Exploration Constraint**: PyInstaller compilation was not executed during this survey, per agent constraints.
2. **Platform Specificity**: Windows OS is the target host; macOS bundle (`BUNDLE(...)`) in `desktop/mimo.spec` was not evaluated for macOS signing/entitlements.
3. **PyInstaller Dynamic Hooking**: PyInstaller runtime hooks for binary libraries (e.g., OpenCV DLLs or PySide/Tkinter extensions) depend on the exact virtual environment setup where PyInstaller is run.

---

## 4. Conclusion

Requirement R2 PyInstaller build setup is structurally well-designed around `desktop/mimo.spec`, but requires three mandatory fixes prior to final compilation:
1. **Fix `numpy` exclusion**: Remove `"numpy"` from `excludes` in `desktop/mimo.spec` line 126.
2. **Deprecate incomplete build configs**: Use `pyinstaller desktop/mimo.spec` as the standard build command instead of `Mimo.spec` or `desktop/build.py`.
3. **Fix zombie process hazard**: Refactor `desktop/main_desktop.py` main loop and update `_on_quit` in `desktop/tray.py` to invoke clean shutdown (`_shutdown()`) before process termination.

---

## 5. Verification Method

### 5.1 Pre-Build Inspection Commands
1. Inspect `desktop/mimo.spec` to confirm `numpy` is not excluded:
   ```powershell
   Select-String -Path "desktop\mimo.spec" -Pattern "numpy"
   ```
2. Verify static files exist in `static/`:
   ```powershell
   Get-ChildItem -Path "static"
   ```

### 5.2 Build Command
Run PyInstaller using `desktop/mimo.spec`:
```powershell
pyinstaller desktop/mimo.spec
```

### 5.3 Post-Build Verification
1. Verify executable artifact exists:
   - Check file `dist/Mimo/Mimo.exe`
   - Check directory `dist/Mimo/_internal/static/dashboard.html`
2. Test launch and clean shutdown:
   - Launch `dist/Mimo/Mimo.exe`
   - Verify splash screen displays, FastAPI starts, and pywebview dashboard window opens.
   - Right-click system tray icon -> Quit Mimo.
   - Check Task Manager (`Get-Process Mimo -ErrorAction SilentlyContinue`) to confirm zero lingering `Mimo.exe` processes exist.
