# Desktop App Testing Investigation (R2 & R3) — Analysis Report

## Executive Summary
This report presents a comprehensive investigation of the Mimo Desktop Application located in `desktop/` for requirements R2 (Isolated Test Environments) and R3 (Comprehensive Mocked Unit Testing). It covers codebase architecture, backend API endpoints including `https://mimo-e8u2.onrender.com`, initialization flows, virtual environment setup, dependencies, and a complete design for a unit test suite in `desktop/tests/` that mocks all backend interactions to achieve 100% test success when executing `pytest desktop/tests/`.

---

## 1. Desktop App Architecture & Initialization Analysis

The `desktop/` application is structured into modular Python components handling window management, system tray operations, settings, single-instance execution, notifications, and executable packaging.

### Codebase Inventory (`desktop/` Files)
- **`desktop/main_desktop.py`**: Primary application entry point. Coordinates the 11-step startup sequence:
  1. Single-instance acquisition via `single_instance.py`
  2. Logging configuration (console and file output in `%LOCALAPPDATA%/Mimo/logs` or `~/.mimo`)
  3. Splash screen initialization using Tkinter (`splash.py`)
  4. FastAPI/Uvicorn server launch in a background daemon thread
  5. Polling `/health` endpoint until server is ready (timeout: 40s)
  6. Webview window creation via `window_manager.py` (PyWebview)
  7. System tray initialization in a daemon thread via `tray.py` (Pystray)
  8. Native OS startup notification via `notifications.py`
  9. Execution of PyWebview event loop on the main thread
  10. Intercepting window close events to keep the application running in system tray
  11. Clean shutdown on tray exit via `atexit` handlers
- **`desktop/settings_manager.py`**: Manages `.env` configuration file reading/writing. Masking for sensitive keys (e.g. `OPENAI_API_KEY`), UI section groupings (`AI`, `Hardware`, `Voice`, `Behavior Thresholds`, `Schedule`, `Advanced`), and input type inferences.
- **`desktop/autostart.py`**: Cross-platform OS autostart registration supporting Windows Registry (`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`), macOS LaunchAgent plist (`~/Library/LaunchAgents/com.mimo.app.plist`), and Linux desktop entries (`~/.config/autostart/mimo.desktop`).
- **`desktop/notifications.py`**: Cross-platform OS notifications via `plyer`. Includes automatic suppression during pytest runs via `PYTEST_CURRENT_TEST in os.environ`.
- **`desktop/single_instance.py`**: Single-instance lock mechanism using Windows Named Mutex (`CreateMutexW`) on Windows and POSIX `fcntl` file lock (`~/.mimo/mimo.pid`) on Unix/macOS.
- **`desktop/splash.py`**: Tkinter-based splash screen displaying animated progress dots during app startup.
- **`desktop/tray.py`**: System tray icon using `pystray`. Includes background stats polling thread (`_stats_loop`), pause/resume toggle, autostart toggle, and settings navigation.
- **`desktop/window_manager.py`**: Wraps PyWebview browser window lifecycle. Intercepts window close to hide window to tray, brings window to front, or falls back to standard browser.
- **`desktop/icon_generator.py`**: Dynamic RGBA icon generator using `Pillow` (PIL) for `active`, `paused`, and `alert` tray icon states.
- **`desktop/build.py` & `desktop/mimo.spec`**: PyInstaller packaging script and spec file for bundling the standalone tracker executable (`MimoDesktopTracker`).

---

## 2. API Endpoints & Backend URL Analysis (`mimo-e8u2.onrender.com`)

The desktop app interacts with the backend server over HTTP/REST. While local execution defaults to `http://127.0.0.1:8000`, the remote production backend is deployed at **`https://mimo-e8u2.onrender.com`**.

### Remote Backend URL
- **Production Backend URL**: `https://mimo-e8u2.onrender.com`
- **Configurable Environment Variable**: `MIMO_CLOUD_URL` or `MIMO_API_BASE_URL` (defaults to `http://127.0.0.1:8000` locally or `https://mimo-e8u2.onrender.com` in production).

### Desktop API Endpoint Inventory
| Endpoint | Method | Component Source | Function / Purpose | Expected Response |
| --- | --- | --- | --- | --- |
| `/health` | GET | `main_desktop.py` | Server health check during app initialization | `{"status": "healthy"}` |
| `/reports/stats` | GET | `tray.py` | Live stats update for system tray menu | `{"focus_score": 85.5, "letter_grade": "A"}` |
| `/assignments/upcoming?days=14` | GET | `tray.py` | Pending assignment count for system tray menu | `[{"id": 1, "title": "Math HW"}]` |
| `/monitoring/pause` | POST | `tray.py` | Pause background activity tracking | `{"ok": true, "status": "paused"}` |
| `/monitoring/resume` | POST | `tray.py` | Resume background activity tracking | `{"ok": true, "status": "active"}` |
| `/screen/mock` | POST | `build.py` (tracker client) | Push screen event data to cloud backend | `{"ok": true}` |
| `/settings/data` | GET | `settings_manager.py` | Load settings JSON for desktop UI | `{"sections": [...]}` |
| `/settings/save` | POST | `settings_manager.py` | Save individual key to `.env` | `{"ok": true, "key": "..."}` |
| `/settings/save-all` | POST | `settings_manager.py` | Bulk save settings dictionary | `{"ok": true, "saved": [...], "failed": []}` |

---

## 3. Isolated `.venv` Environment & `test_requirements.txt` Specifications

To fulfill **Requirement R2**, an isolated Python virtual environment (`.venv`) and a dedicated test dependencies file (`test_requirements.txt`) must be created.

### `test_requirements.txt` Contents
```text
# ── Mimo Desktop Test Suite Dependencies ──────────────────────────────
pytest==8.3.4
pytest-mock==3.14.0
requests-mock==1.12.1
respx==0.21.1
httpx==0.27.0
requests==2.32.3
pystray==0.19.5
Pillow==10.3.0
pywebview==5.1
plyer==2.1.0
python-dotenv==1.0.1
fastapi==0.111.0
uvicorn==0.29.0
psutil==5.9.8
```

### Environment Setup Commands

#### Windows (PowerShell):
```powershell
# Navigate to project root
cd c:\Users\samee\projects\Mimo

# Create isolated Python virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Upgrade pip and install test requirements
python -m pip install --upgrade pip
pip install -r test_requirements.txt
```

#### Windows (CMD):
```cmd
cd c:\Users\samee\projects\Mimo
python -m venv .venv
.\.venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r test_requirements.txt
```

#### Linux / macOS:
```bash
cd /path/to/Mimo
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r test_requirements.txt
```

---

## 4. Unit Test Suite Design for `desktop/tests/`

To fulfill **Requirement R3**, a dedicated test suite under `desktop/tests/` will be established. The suite will test all desktop components while mocking all remote and local network calls to `https://mimo-e8u2.onrender.com` and `http://127.0.0.1:8000`.

### Directory Layout
```text
desktop/
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Shared fixtures & backend API mock interceptors
│   ├── test_backend_api_mock.py   # Mocks mimo-e8u2.onrender.com API endpoints
│   ├── test_desktop_app_init.py   # Tests main_desktop.py startup & server polling
│   └── test_desktop_ui_services.py# Tests WindowManager, MimoTray, Settings, Notifications, Autostart
```

---

## 5. Proposed Unit Test File Specifications

### 5.1 `desktop/tests/conftest.py`
```python
"""
Pytest configuration and shared fixtures for desktop/tests/.
Mocks backend API endpoints (mimo-e8u2.onrender.com and localhost)
and isolates environment variables and GUI calls.
"""
import os
import pytest
import httpx

REMOTE_BACKEND_URL = "https://mimo-e8u2.onrender.com"
LOCAL_BACKEND_URL  = "http://127.0.0.1:8000"

@pytest.fixture(autouse=True)
def set_testing_env(monkeypatch, tmp_path):
    """Set environment variables for isolated desktop testing."""
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "true")
    monkeypatch.setenv("MIMO_CLOUD_URL", REMOTE_BACKEND_URL)
    monkeypatch.setenv("MIMO_DISABLE_NOTIFICATIONS", "1")
    
    # Isolate .env file
    env_file = tmp_path / ".env"
    env_file.write_text("EOD_REPORT_HOUR=22\nNO_HARDWARE=1\nNO_VOICE=1\n")
    import desktop.settings_manager as sm
    monkeypatch.setattr(sm, "_ENV_PATH", str(env_file))
    return env_file

@pytest.fixture
def mock_render_backend(monkeypatch):
    """
    Mock responses for https://mimo-e8u2.onrender.com and http://127.0.0.1:8000
    using httpx monkeypatching.
    """
    class MockResponse:
        def __init__(self, status_code, json_data):
            self.status_code = status_code
            self._json_data = json_data
            self.text = str(json_data)
        def json(self):
            return self._json_data

    def fake_get(url, **kwargs):
        if "/health" in url:
            return MockResponse(200, {"status": "healthy"})
        elif "/reports/stats" in url:
            return MockResponse(200, {"focus_score": 92.5, "letter_grade": "A"})
        elif "/assignments/upcoming" in url:
            return MockResponse(200, [{"id": 1, "title": "Calculus HW", "due_date": "2026-08-10"}])
        elif "/settings/data" in url:
            return MockResponse(200, {"sections": []})
        return MockResponse(404, {"error": "Not Found"})

    def fake_post(url, **kwargs):
        if "/monitoring/pause" in url:
            return MockResponse(200, {"ok": True, "status": "paused"})
        elif "/monitoring/resume" in url:
            return MockResponse(200, {"ok": True, "status": "active"})
        elif "/screen/mock" in url:
            return MockResponse(200, {"ok": True, "synced": True})
        elif "/settings/save" in url:
            return MockResponse(200, {"ok": True})
        return MockResponse(404, {"error": "Not Found"})

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr(httpx, "post", fake_post)
    return REMOTE_BACKEND_URL
```

### 5.2 `desktop/tests/test_backend_api_mock.py`
```python
"""
Unit tests mocking https://mimo-e8u2.onrender.com backend API responses.
"""
import httpx
import requests

def test_mock_render_backend_health_check(mock_render_backend):
    url = f"{mock_render_backend}/health"
    response = httpx.get(url)
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_mock_render_backend_reports_stats(mock_render_backend):
    url = f"{mock_render_backend}/reports/stats"
    response = httpx.get(url)
    assert response.status_code == 200
    data = response.json()
    assert data["focus_score"] == 92.5
    assert data["letter_grade"] == "A"

def test_mock_render_backend_assignments(mock_render_backend):
    url = f"{mock_render_backend}/assignments/upcoming?days=14"
    response = httpx.get(url)
    assert response.status_code == 200
    assignments = response.json()
    assert len(assignments) == 1
    assert assignments[0]["title"] == "Calculus HW"

def test_mock_render_backend_monitoring_toggle(mock_render_backend):
    pause_res = httpx.post(f"{mock_render_backend}/monitoring/pause")
    assert pause_res.status_code == 200
    assert pause_res.json()["status"] == "paused"

    resume_res = httpx.post(f"{mock_render_backend}/monitoring/resume")
    assert resume_res.status_code == 200
    assert resume_res.json()["status"] == "active"

def test_mock_screen_tracker_cloud_sync(requests_mock):
    cloud_url = "https://mimo-e8u2.onrender.com"
    requests_mock.post(f"{cloud_url}/screen/mock", json={"ok": True}, status_code=200)
    
    res = requests.post(f"{cloud_url}/screen/mock", json={"app": "VSCode", "title": "main.py"})
    assert res.status_code == 200
    assert res.json()["ok"] is True
```

### 5.3 `desktop/tests/test_desktop_app_init.py`
```python
"""
Unit tests for desktop application startup sequence and server polling logic.
"""
from desktop.main_desktop import _wait_for_server, STARTUP_TIMEOUT

def test_wait_for_server_healthy(mock_render_backend):
    assert _wait_for_server(timeout=2, splash=None) is True

def test_wait_for_server_timeout(monkeypatch):
    import httpx
    def failing_get(url, timeout=2):
        raise ConnectionError("Server unreachable")
    monkeypatch.setattr(httpx, "get", failing_get)

    assert _wait_for_server(timeout=1, splash=None) is False

def test_single_instance_acquisition():
    from desktop.single_instance import acquire, release
    assert acquire() is True
    release()
```

### 5.4 `desktop/tests/test_desktop_ui_services.py`
```python
"""
Unit tests for WindowManager, MimoTray, SettingsManager, Notifications, and Autostart.
"""
from desktop.window_manager import WindowManager
from desktop.tray import MimoTray
from desktop.settings_manager import load_settings, save_setting
from desktop.notifications import notify
from desktop.autostart import get_executable_path

def test_window_manager_fallback(monkeypatch):
    wm = WindowManager(url="https://mimo-e8u2.onrender.com")
    opened = []
    import desktop.window_manager as wm_mod
    monkeypatch.setattr(wm_mod.webbrowser, "open", lambda url: opened.append(url))
    wm.open()
    assert len(opened) == 1
    assert opened[0] == "https://mimo-e8u2.onrender.com"

def test_mimo_tray_stats_update():
    tray = MimoTray()
    tray.update_stats(focus_score=88.4, grade="A", assignments=2)
    assert tray._focus_score == 88
    assert tray._grade == "A"
    assert tray._assignments == 2

def test_settings_manager_masking():
    settings = load_settings(mask_sensitive=True)
    assert "OPENAI_API_KEY" in settings

def test_notifications_suppressed_in_pytest():
    assert notify("Test Title", "Test Message") is False

def test_autostart_executable_path():
    path = get_executable_path()
    assert isinstance(path, str)
    assert len(path) > 0
```

---

## 6. Execution & Verification Method

To verify the desktop unit test suite independently:

1. **Activate `.venv`**:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
2. **Execute pytest on `desktop/tests/`**:
   ```powershell
   pytest desktop/tests/ -v
   ```
3. **Expected Verification Result**:
   - 100% pass rate across all unit test cases.
   - Zero unhandled exceptions or crashes.
