# 🖥 Mimo Desktop App

This guide covers running Mimo as a real desktop application — system tray icon, native window, auto-start on boot, and a packaged `.exe`/`.app`/binary you can hand to someone else.

If you just want the server + browser dashboard (no tray, no packaging), use `python run_server.py` instead — see the main README.

---

## Three ways to run Mimo

| Mode | Command | What you get |
|---|---|---|
| **Server only** | `python run_server.py` | Backend + browser dashboard. No tray, no native window. Best for development. |
| **Desktop app (dev)** | `python run_desktop.py` | Full experience: splash screen, native window, system tray, notifications. Runs from source. |
| **Packaged app** | `dist/Mimo/Mimo.exe` (after building) | Same as above, but a real installable app — no Python needed on the target machine. |

---

## Running the desktop app from source

### 1. Install base + desktop dependencies

```bash
pip install -r requirements.txt
pip install -r requirements_desktop.txt
```

### 2. Run the OS-specific setup script (one time only)

```bash
chmod +x desktop/setup_desktop.sh
./desktop/setup_desktop.sh
```

This installs system packages the tray icon needs:
- **Linux:** GTK3, AppIndicator, libnotify (for the tray icon + notifications)
- **macOS:** python-tk (for the splash screen)
- **Windows:** nothing extra needed

### 3. Set your API key

```bash
cp .env.example .env
nano .env   # add OPENAI_API_KEY=sk-...
```

### 4. Launch

```bash
python run_desktop.py
```

What happens:
1. A dark splash screen appears ("Starting Mimo…")
2. The FastAPI server boots in the background
3. Once healthy, a native window opens showing the dashboard
4. A flame icon appears in your system tray
5. You get a "Mimo started" notification

**Closing the window doesn't quit Mimo** — it keeps monitoring in the tray. Click the tray icon → "Open Mimo" to bring the window back. Click "Quit Mimo" to fully exit.

---

## System tray menu

Right-click (or left-click on some platforms) the flame icon:

| Item | Action |
|---|---|
| **Open Mimo** | Shows the dashboard window |
| Focus 76/100, Grade B | Live stats, updates every 60s |
| Assignments 3 pending | Live count |
| **Pause/Resume monitoring** | Stops/starts screen + camera tracking |
| **Settings** | Opens the settings page in your browser |
| **Start with system** | Toggle auto-start on boot (checkmark shows current state) |
| **Quit Mimo** | Fully exits — stops all background processes |

---

## Settings page

Open via tray menu → Settings, or go to `http://localhost:8000/settings` directly.

You can change, without editing `.env` by hand:
- OpenAI API key (with a "Test key" button to verify it works)
- Hardware toggle (enable/disable ESP32-CAM)
- Voice toggle (enable/disable microphone)
- ESP32-CAM stream URL
- Roast timing thresholds
- End-of-day report hour
- Reminder check interval

Changes save to `.env` immediately. Most take effect on the next background task cycle; API key changes need "Restart services" (link at the bottom of the page).

---

## Building a distributable app

This creates a folder/app you can zip and send to someone — they don't need Python installed.

### 1. Install PyInstaller

```bash
pip install pyinstaller
```

(Already included in `requirements_desktop.txt`.)

### 2. Run the build script

```bash
python desktop/build.py
```

This runs pre-flight checks (Python version, dependencies, icons) then builds.

Options:
```bash
python desktop/build.py --clean        # wipe dist/ and build/ first
python desktop/build.py --check-only   # just run checks, don't build
```

### 3. Find your build

| Platform | Output |
|---|---|
| Windows | `dist/Mimo/Mimo.exe` |
| macOS | `dist/Mimo.app` (also zipped to `dist/Mimo_macOS.zip`) |
| Linux | `dist/Mimo/Mimo` |

### 4. Before running the built app

Copy `.env.example` to `.env` inside the `dist/Mimo/` folder and add your API key:

```bash
cp dist/Mimo/.env.example dist/Mimo/.env
nano dist/Mimo/.env
```

### 5. Run it

```bash
# Windows
dist\Mimo\Mimo.exe

# macOS
open dist/Mimo.app

# Linux
./dist/Mimo/Mimo
```

---

## Building on each platform

PyInstaller builds for the platform you run it on — you can't cross-compile. To get all three builds you need to run the build script on Windows, macOS, and Linux separately (or use CI with three runners).

### Windows-specific notes

If Windows Defender flags the `.exe` as unrecognized, that's normal for unsigned PyInstaller builds. For real distribution, sign the executable with a code-signing certificate.

### macOS-specific notes

Unsigned `.app` bundles get a Gatekeeper warning ("can't be opened because it is from an unidentified developer"). Right-click → Open bypasses this once. For real distribution, you need an Apple Developer account ($99/year) to sign and notarize.

The build sets `LSUIElement: True` in the bundle's Info.plist — this hides Mimo from the Dock and Cmd+Tab switcher, since it's a tray-only app.

### Linux-specific notes

The tray icon needs `libappindicator3` and a desktop environment with tray support (GNOME needs the "AppIndicator and KStatusNotifierItem Support" extension; KDE and most others work out of the box).

---

## Auto-start on boot

Toggle from the tray menu ("Start with system"), or call the API directly:

```python
from desktop.autostart import enable, disable, is_enabled
enable()        # registers Mimo to start when you log in
disable()       # removes it
is_enabled()    # check current state
```

Implementation per platform:
- **Windows:** Registry key in `HKEY_CURRENT_USER\...\Run`
- **macOS:** LaunchAgent plist in `~/Library/LaunchAgents/`
- **Linux:** `.desktop` file in `~/.config/autostart/`

---

## Single instance protection

Mimo prevents itself from running twice. If you double-click the app while it's already running, you'll see a dialog: "Mimo is already running. Check the system tray icon."

This uses a named mutex on Windows and an `flock`-based PID file (`~/.mimo/mimo.pid`) on macOS/Linux.

---

## Architecture of the desktop layer

```
desktop/
├── main_desktop.py      ← entry point, orchestrates startup sequence
├── splash.py             ← tkinter loading screen (no extra install)
├── window_manager.py     ← pywebview window lifecycle (hide-on-close)
├── tray.py                ← pystray system tray icon + menu
├── icon_generator.py     ← draws the flame icon with Pillow (no image files needed)
├── notifications.py      ← cross-platform native notifications (plyer)
├── autostart.py           ← Windows Registry / macOS LaunchAgent / Linux .desktop
├── single_instance.py    ← prevents double-launch (mutex / flock)
├── settings_manager.py   ← reads/writes .env safely
├── build.py                ← PyInstaller build script with pre-flight checks
└── mimo.spec               ← PyInstaller build specification
```

Startup sequence (`main_desktop.py`):
1. Single-instance check
2. Splash screen shown (separate thread)
3. FastAPI server started (separate thread)
4. Poll `/health` until ready (up to 40s timeout)
5. pywebview window created
6. System tray started (separate thread)
7. Startup notification fired
8. Splash closed
9. pywebview event loop runs on main thread (blocking)
10. When all windows close, app continues via tray (daemon threads keep running)

---

## Troubleshooting

**Splash screen never closes / app hangs on startup**
The server probably failed to bind to port 8000. Check if something else is using that port: `lsof -i :8000` (Mac/Linux) or `netstat -ano | findstr :8000` (Windows).

**No tray icon appears (Linux)**
Your desktop environment may be missing AppIndicator support. Install `gir1.2-appindicator3-0.1` (Ubuntu/Debian) or check if GNOME needs the AppIndicator extension enabled.

**"Mimo already running" but it's not**
A stale lock file may exist. Delete `~/.mimo/mimo.pid` and try again.

**Window doesn't reopen after closing**
Click the tray icon's "Open Mimo" menu item — closing the window only hides it, it doesn't destroy the app.

**Built .exe is huge (200MB+)**
This is normal for PyInstaller bundles with mediapipe/opencv. The bundle includes the entire Python runtime plus all ML libraries. To shrink it, exclude `NO_HARDWARE=1` users' camera/CV dependencies from the build (advanced — requires a separate light build profile).
