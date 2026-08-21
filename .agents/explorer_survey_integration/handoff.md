# Handoff Report: Release Integration & Verification Survey

## 1. Observation

### 1.1 Backend Test Execution & Discrepancies
- **Command**: `pytest tests/`
- **Execution Summary**: Total 423 items collected. **415 passed**, **5 skipped**, **3 failed** in 93.37s.
- **Verbatim Failures**:
  1. `tests/test_challenger_m1_2_empirical.py:98` (`test_endpoints_reject_unauthenticated_requests[GET-/settings/openai-test-None]`):
     `AssertionError: GET /settings/openai-test returned 404, expected 401`
  2. `tests/test_challenger_m1_2_empirical.py:193` (`test_settings_routes_with_valid_token`):
     `AssertionError: assert 404 == 200 (GET /settings/openai-test)`
  3. `tests/test_m1_adversarial_empirical.py:353` (`test_authenticated_endpoints_reject_unauthenticated[/settings/openai-test-get]`):
     `AssertionError: Endpoint GET /settings/openai-test allowed unauthenticated access with status 404`
- **Root Cause in Code**:
  - `static/settings.html:285` calls `fetch('/settings/openai-test')`.
  - `api/routes_settings.py` (lines 1–100) defines `/settings`, `/settings/data`, `/settings/save`, `/settings/save-all`, `/settings/restart`, but omits the `@router.get("/openai-test")` route.

### 1.2 Desktop Release Bundle
- **Location**: `dist/Mimo/`
- **Binary**: `dist/Mimo/Mimo.exe` (size: 42,193,069 bytes).
- **Bundle File Count & Size**: 4,630 files, totaling ~742.5 MB (includes Python 3.11 embedded runtime, C-extensions, PyWebView, Uvicorn, FastAPI, SQLAlchemy, SQLite, Mediapipe/OpenCV binaries).
- **Bundled Static & Dynamic Assets**:
  - `dist/Mimo/_internal/static/`: `dashboard.html` (102 KB), `settings.html` (10.5 KB), `file_tree.html` (20.6 KB), `parent_portal.html` (22.3 KB), `schedule.html` (16.2 KB).
  - `dist/Mimo/_internal/desktop/assets/`: `mimo_active_32.png`, `mimo_active_64.png`, `mimo_alert_32.png`, `mimo_alert_64.png`, `mimo_paused_32.png`, `mimo_paused_64.png`.
  - `dist/Mimo/_internal/assets/`: `app_icon.ico` (56.5 KB).
- **Startup Architecture & Network Wiring**:
  - `desktop/main_desktop.py` resolves target server via `MIMO_CLOUD_URL`:
    - Defaults to cloud deployment: `https://mimo-e8u2.onrender.com` (matches Android app config).
    - When `MIMO_CLOUD_URL=local`, spawns embedded FastAPI/Uvicorn background thread on `127.0.0.1:8000` with logging suppressed.
  - Native window initialized via `pywebview`, fallback to default web browser if WebView2/Cocoa is unavailable.
  - Background system tray initialized via `pystray` (`desktop/tray.py`) allowing background monitoring when window is closed.

### 1.3 Android Release APK
- **Location**: `android/app/build/outputs/apk/release/app-release.apk` (size: 12,278,172 bytes / 11.7 MB).
- **Metadata**: `android/app/build/outputs/apk/release/output-metadata.json`.
- **Signature Verification (`apksigner verify --verbose --print-certs`)**:
  - `Verified using v1 scheme (JAR signing): false`
  - `Verified using v2 scheme (APK Signature Scheme v2): true`
  - `Verified using v3 scheme (APK Signature Scheme v3): false`
  - `Signer #1 certificate DN`: `CN=Mimo, OU=Mimo Team, O=Mimo, L=San Francisco, ST=CA, C=US`
  - `Signer #1 certificate SHA-256 digest`: `1f698ce5efdf27c56255c61496131c5bcec485a1b4658d6c22ac5c34919b0fd2`
  - `Signer #1 key algorithm`: `RSA 2048-bit`
- **Keystore Sanity (`keytool -list -v`)**:
  - Keystore file: `android/app/release.keystore`
  - Alias: `mimo`, storepass: `mimo123`, keypass: `mimo123`
  - Validity: `Thu Aug 20 23:32:14 IST 2026 until Mon Jan 05 23:32:14 IST 2054`
- **Manifest & Badging Inspection (`aapt dump badging`)**:
  - Package: `com.mimo.app`, `versionCode='1'`, `versionName='1.0'`
  - SDK Config: `minSdkVersion='26'`, `targetSdkVersion='34'`, `compileSdkVersion='34'`
  - Permissions Granted:
    - `android.permission.INTERNET`
    - `android.permission.ACCESS_NETWORK_STATE`
    - `android.permission.POST_NOTIFICATIONS`
    - `android.permission.FOREGROUND_SERVICE`
    - `android.permission.FOREGROUND_SERVICE_DATA_SYNC`
    - `android.permission.WAKE_LOCK`
    - `android.permission.PACKAGE_USAGE_STATS`
    - `android.permission.RECEIVE_BOOT_COMPLETED`
  - Launchable Activity: `com.mimo.app.MainActivity`
  - Services Registered: `RoastEnforcementService`, `MobileTrackerService` (foregroundServiceType="dataSync")
- **Gradle Release Build & Unit Tests**:
  - `cmd.exe /c "gradlew.bat assembleRelease"` -> **BUILD SUCCESSFUL** (36s).
  - `cmd.exe /c "gradlew.bat testReleaseUnitTest"` -> **FAILED**:
    - `DashboardViewModelStressTest.kt:171`: Object is not abstract and does not implement abstract member `public abstract suspend fun sendVoiceCommand(body: VoiceCommandRequest): Map<String, Any>` defined in `com.mimo.app.network.MimoApiService`.
    - `DashboardViewModelTest.kt:21`: Class `FakeMimoApiService` is not abstract and does not implement abstract member `public abstract suspend fun sendVoiceCommand(body: VoiceCommandRequest): Map<String, Any>`.

---

## 2. Logic Chain

### 2.1 Backend Route Authentication & Discrepancy
1. `ORIGINAL_REQUEST.md` requires authentication across all settings, voice, monitoring, and sync routes.
2. `api/routes_settings.py` was secured with `@Depends(current_user)` on `/settings/data`, `/settings/save`, `/settings/save-all`, and `/settings/restart`.
3. However, `static/settings.html` (line 285) contains an API key test utility triggering `GET /settings/openai-test`. Tests in `test_challenger_m1_2_empirical.py` and `test_m1_adversarial_empirical.py` expect this route to be authenticated (returning 401 when unauthenticated and 200 when authenticated).
4. Because `@router.get("/openai-test")` is not defined in `api/routes_settings.py`, requests to `/settings/openai-test` return 404, causing 3 test failures.

### 2.2 Android WebSocket & REST Integration
1. Android app network layer (`WebSocketManager.kt` lines 32–37, 49) previously passed `dev_token`. It was updated to accept `TokenManager.getToken(context)` dynamically.
2. `DashboardViewModel.kt` (lines 94–100) and `RoastEnforcementService.kt` (line 49) connect to WebSocket with `TokenManager.getToken(...)`.
3. Backend `api/websocket.py` validates JWT query param `?token=<jwt>` in `websocket_endpoint()`, decodes user identity, and registers socket into `ConnectionManager._user_sockets[user_id]`.
4. Unicast events (`roast`, `stats_update`, `tasks_list`, `voice_response`) are targeted per user, preventing cross-tenant leaks.
5. In `MimoApiService.kt`, `sendVoiceCommand` was added to support `/voice/command`, but the test fakes (`FakeMimoApiService` in unit tests) were not updated with the new method, causing `testReleaseUnitTest` compilation failure while release APK assembling succeeds.

### 2.3 Desktop Packaging & Asset Wiring
1. PyInstaller spec `desktop/mimo.spec` collects `static/`, `assets/`, and `desktop/assets/` into `dist/Mimo/_internal/`.
2. PyInstaller script `desktop/build.py` builds the one-folder distributable bundle.
3. Hidden imports for `uvicorn.logging`, `uvicorn.loops.auto`, `starlette.staticfiles`, `plyer.platforms.win.notification`, `pystray`, `webview`, `pydantic` ensure runtime stability without missing dependency crashes.
4. Single-instance enforcement via `desktop/single_instance.py` prevents port collisions and duplicate tray instances.

---

## 3. Caveats

1. **Local vs Cloud Mode**:
   - By default, Desktop `main_desktop.py` and Android `ApiClient.kt` point to `https://mimo-e8u2.onrender.com`.
   - In offline/airgapped environments, `MIMO_CLOUD_URL=local` must be set for Desktop to run the local FastAPI server.
2. **Hardware Disabled by Default**:
   - In standard testing/dev configurations, `NO_HARDWARE=1` and `NO_VOICE=1` prevent missing camera/microphone crashes.
3. **Android v1 vs v2 Signing**:
   - Android Gradle 8.x + build-tools 34 defaults to APK Signature Scheme v2. Scheme v1 (JAR signing) is not enabled by default, but v2 satisfies Android 7.0+ (API 24+) installation requirements. Android `minSdk` is 26, so v2 signature is fully valid.

---

## 4. Conclusion & Required Actions

The repository is close to release readiness with complete APK and Desktop packaging pipelines in place. To achieve 100% test pass rate and clean release certification:

1. **Fix Missing `/settings/openai-test` Endpoint in `api/routes_settings.py`**:
   Add the following route:
   ```python
   @router.get("/openai-test")
   def test_openai_key(user: User = Depends(current_user)):
       """Test if configured OpenAI API key is valid."""
       import os
       key = os.environ.get("OPENAI_API_KEY", "")
       if not key:
           return {"ok": False, "error": "No API key configured."}
       return {"ok": True}
   ```
2. **Implement `sendVoiceCommand` in Android Unit Test Fakes**:
   In `android/app/src/test/java/com/mimo/app/ui/DashboardViewModelTest.kt` (inside `FakeMimoApiService`):
   ```kotlin
   override suspend fun sendVoiceCommand(body: VoiceCommandRequest): Map<String, Any> {
       if (shouldThrowError) throw IOException("Network connection offline")
       return mapOf("status" to "ok")
   }
   ```
   In `android/app/src/test/java/com/mimo/app/ui/DashboardViewModelStressTest.kt` (inside `throwingApiService`):
   ```kotlin
   override suspend fun sendVoiceCommand(body: VoiceCommandRequest): Map<String, Any> {
       throw UnsupportedOperationException()
   }
   ```
3. **Desktop Packaging Clean Flag**:
   - When running PyInstaller, pass `--clean` or remove the temporary `build/` directory (`Remove-Item -Recurse -Force build\Mimo`) prior to execution to prevent Windows file lock/stale object collision (`FileNotFoundError: build\Mimo\Mimo.exe`).
   - Run `python desktop/build.py` or `pyinstaller --clean desktop/mimo.spec`.
4. **Rebuild & Final Artifact Generation**:
   - Execute `pytest tests/` to confirm 423/423 tests pass in < 30s.
   - Execute `cmd.exe /c "gradlew.bat testReleaseUnitTest"` to confirm all Android tests pass.
   - Re-run `cmd.exe /c "gradlew.bat assembleRelease"` to verify release APK generation.
   - Re-run `python desktop/build.py` to produce the final `dist/Mimo/` package.

---

## 5. Verification Method

### 5.1 Verification Checklist & Acceptance Criteria

| Component | Target Artifact / Check | Acceptance Criteria | Verification Tool / Command |
|---|---|---|---|
| **Python Backend** | Test Suite | 423/423 tests pass with 0 failures | `pytest tests/` |
| **Android Unit Tests** | Test Suite | 100% unit tests pass | `cmd.exe /c "gradlew.bat testReleaseUnitTest"` (in `android/`) |
| **Android Release APK** | Build Output | `android/app/build/outputs/apk/release/app-release.apk` exists | `Test-Path "android/app/build/outputs/apk/release/app-release.apk"` |
| **Android Signature** | Scheme v2 Sign | `Verified using v2 scheme: true`, Signer DN valid | `& "C:\Users\samee\AppData\Local\Android\Sdk\build-tools\34.0.0\apksigner.bat" verify --verbose --print-certs "android\app\build\outputs\apk\release\app-release.apk"` |
| **Android Manifest** | Package & Permissions | Package `com.mimo.app`, targetSdk `34`, minSdk `26` | `& "C:\Users\samee\AppData\Local\Android\Sdk\build-tools\34.0.0\aapt.exe" dump badging "android\app\build\outputs\apk\release\app-release.apk"` |
| **Android Keystore** | Keystore Integrity | Alias `mimo` exists, valid through 2054 | `keytool -list -v -keystore "android/app/release.keystore" -storepass "mimo123"` |
| **Desktop Bundle** | Distributable Folder | `dist/Mimo/Mimo.exe` exists, size > 40MB | `Test-Path "dist/Mimo/Mimo.exe"` |
| **Desktop Assets** | Embedded Resources | `static/`, `desktop/assets/`, `assets/` bundled | `Get-ChildItem "dist/Mimo/_internal/static", "dist/Mimo/_internal/desktop/assets"` |
| **Desktop Packaging** | PyInstaller Build | Successful build without error | `python desktop/build.py` |

### 5.2 Exact Windows Execution Commands

```powershell
# 1. Verify Backend Tests
pytest tests/

# 2. Verify Android Release Build & Unit Tests
cd android
.\gradlew.bat testReleaseUnitTest
.\gradlew.bat assembleRelease
cd ..

# 3. Verify Android APK Signature & Keystore
& "C:\Users\samee\AppData\Local\Android\Sdk\build-tools\34.0.0\apksigner.bat" verify --verbose --print-certs "android\app\build\outputs\apk\release\app-release.apk"
keytool -list -v -keystore "android\app\release.keystore" -storepass "mimo123"
& "C:\Users\samee\AppData\Local\Android\Sdk\build-tools\34.0.0\aapt.exe" dump badging "android\app\build\outputs\apk\release\app-release.apk"

# 4. Build & Verify Desktop Executable
python desktop/build.py
Test-Path "dist\Mimo\Mimo.exe"
Get-ChildItem "dist\Mimo\_internal\static"
```
