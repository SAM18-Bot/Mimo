# Technical Findings & Handoff Report — Explorer 3

## 1. Observation

### Requirement R5 — Android WebSocket Auth & Build Setup
- **`android/app/src/main/java/com/mimo/app/network/WebSocketManager.kt`**:
  - Line 29: Hardcoded connection URL default `private var wsUrl: String = "wss://mimo-e8u2.onrender.com/ws?token=dev_token"`.
  - Line 31: `fun connect(url: String = wsUrl)` uses this default URL if no parameter is provided.
- **`android/app/src/main/java/com/mimo/app/data/TokenManager.kt`**:
  - Lines 6-52: Singleton object managing `cachedToken` and `SharedPreferences` ("mimo_prefs" / "jwt_token").
  - Provides `TokenManager.getToken(context: Context? = null): String?`. `TokenManager.init(context)` is called during app startup in `MimoApplication.kt` line 33 and `MainActivity.kt` line 33.
- **Call Sites**:
  - **`android/app/src/main/java/com/mimo/app/ui/DashboardViewModel.kt`**:
    - Lines 26-36: Default parameter `private val webSocketManager: WebSocketManager? = null`. When `DashboardViewModel` is created by standard Jetpack Compose `viewModel()`, `webSocketManager` defaults to `null`, so `webSocketManager?.connect()` at line 90 is never executed.
    - Line 90: `webSocketManager?.connect()` is invoked without passing any token or dynamic URL.
  - **`android/app/src/main/java/com/mimo/app/service/RoastEnforcementService.kt`**:
    - Line 25: `private val webSocketManager = WebSocketManager()`.
    - Line 48: `webSocketManager.connect()` is invoked without arguments, connecting with `dev_token`.
- **Android Gradle Build Setup**:
  - Ran `.\gradlew.bat assembleDebug --no-daemon` in `c:\Users\samee\projects\Mimo\android`.
  - Result: `BUILD SUCCESSFUL in 16s` with 35 tasks executed/up-to-date.

### Requirement R6 — Git Cleanup
- **`.gitignore`**:
  - Line 15: `.venv-test/` is explicitly listed under Python section.
- **Git Tracking Status**:
  - `git ls-files .venv-test/` returned 0 files.
  - `Test-Path .venv-test` evaluated to `False`. No `.venv-test` files are currently tracked or present.

### Acceptance Criteria — Test Suite, Mocking & Coverage Gaps
- **Test Suite Performance**:
  - Running `pytest --durations=10` took >60s for just 22 tests in `test_api.py` before cancellation.
  - **`modules/ai_layer/client.py`**:
    - Lines 25-36: `_MIN_CALL_INTERVAL = 2.0` seconds enforced in `_chat()` via `time.sleep()`. Every test hitting AI features incurs mandatory 2-second rate-limiting delays.
    - Lines 40-91: `_chat()` attempts real HTTP calls via `genai.Client` and `openai.OpenAI`. In testing with fake key (`OPENAI_API_KEY="sk-test-fake"` set in `tests/conftest.py` line 16), these calls fail after network timeout/error latencies.
    - `api/routes_settings.py` lines 98-103: `/settings/openai-test` directly calls `openai.OpenAI(api_key=config.OPENAI_API_KEY).models.list()`, performing real outbound network IO.
- **Route Authentication Coverage Gaps**:
  - **`api/routes_settings.py`**: `/settings/data`, `/settings/save`, `/settings/save-all`, `/settings/openai-test`, `/settings/restart` lack `@Depends(current_user)` authentication. `tests/test_api_desktop.py` calls these routes without `auth_headers`.
  - **`api/routes_monitoring.py`**: `/monitoring/status`, `/monitoring/pause`, `/monitoring/resume` lack `@Depends(current_user)`. `tests/test_api_desktop.py` calls these without `auth_headers`.
  - **`api/routes_voice.py`**: `/voice/status`, `/voice/intents`, `/voice/speak` lack `@Depends(current_user)`. Only `/voice/command` in `tests/test_api.py` currently uses `auth_headers`.

---

## 2. Logic Chain

1. **Android WebSocket Authentication (R5)**:
   - **Premise**: Backend route `/ws` (`main.py` lines 121-133) decodes JWT token passed in the `token` query parameter (`/ws?token=<jwt_token>`).
   - **Issue 1**: `WebSocketManager.kt` defaults `wsUrl` to `"wss://mimo-e8u2.onrender.com/ws?token=dev_token"`.
   - **Issue 2**: `DashboardViewModel.kt` sets `webSocketManager: WebSocketManager? = null` by default, disabling real-time WebSocket updates entirely for UI viewers.
   - **Issue 3**: `RoastEnforcementService.kt` calls `webSocketManager.connect()` with no token parameter, using the hardcoded `dev_token`.
   - **Remediation Strategy**:
     - Modify `WebSocketManager.connect()` to accept `token: String?` and construct the WS URL dynamically (replacing `http` with `ws` from `ApiClient.baseUrl` and appending `?token=$token`). If `token` is not provided, read `TokenManager.getToken(MimoApplication.instance)`.
     - Update `DashboardViewModel`: set default constructor parameter `webSocketManager: WebSocketManager? = WebSocketManager()`, and pass `TokenManager.getToken(application)` when calling `connect()`.
     - Update `RoastEnforcementService`: fetch `TokenManager.getToken(this)` in `onStartCommand()` and pass it to `connect()`.

2. **Git Cleanup (R6)**:
   - **Premise**: `.venv-test/` must be ignored and untracked.
   - **Verification**: `.gitignore` line 15 contains `.venv-test/`, and `git ls-files .venv-test/` returns empty. Git tracking is verified clear.

3. **Pytest Test Suite Acceleration & Coverage (Acceptance Criteria)**:
   - **Premise**: All tests must complete in <30 seconds.
   - **Root Cause**: Unmocked calls to `modules.ai_layer.client._chat()` execute `time.sleep(2.0)` and initiate real external HTTP connections to OpenAI/Gemini servers.
   - **Mock Design in `tests/conftest.py`**:
     - Create an `autouse=True` fixture `@pytest.fixture(autouse=True) def mock_ai_layer(monkeypatch)`.
     - Patch `modules.ai_layer.client._chat` to return mock JSON strings when `json_mode=True` (e.g., mock study recommendations or EOD report dicts) and mock string responses when `json_mode=False`.
     - Patch `openai.OpenAI` and `google.genai.Client` to prevent any outbound network requests during test runs (e.g. `/settings/openai-test`).
   - **Auth Coverage Design**:
     - Update existing tests in `test_api_desktop.py` and `test_api.py` to supply `headers=auth_headers` for `settings`, `monitoring`, and `voice` endpoints.
     - Add new test methods in `test_api_desktop.py` and `test_api.py` verifying that unauthenticated requests (without `Authorization` header) to `/settings/data`, `/settings/save`, `/settings/save-all`, `/monitoring/status`, `/monitoring/pause`, `/monitoring/resume`, `/voice/status`, `/voice/intents`, `/voice/speak`, and `/voice/command` receive `401 Unauthorized` responses.

---

## 3. Caveats

- **Android Device Testing**: The Android build was verified using `./gradlew assembleDebug`. Live WebSocket connection test requires a running backend server and Android emulator/device.
- **Desktop/Mobile Sync Base URL**: `ApiClient.baseUrl` is currently set to `https://mimo-e8u2.onrender.com/`. When testing locally against a local backend server (`http://10.0.2.2:8000/`), `ApiClient.updateBaseUrl()` should be called or configured in settings.

---

## 4. Conclusion

- **R5 Android WebSocket Auth**: Fully identified hardcoded `dev_token` in `WebSocketManager.kt`, missing default instance in `DashboardViewModel.kt`, and missing token retrieval in `RoastEnforcementService.kt`. Android build succeeds via `./gradlew assembleDebug`.
- **R6 Git Cleanup**: `.venv-test/` is confirmed present in `.gitignore` (line 15) and clean from git tracking.
- **Acceptance Criteria Test Performance & Coverage**:
  - Slow tests are caused by `_chat` rate-limit sleeps (2.0s) and unmocked external API calls to OpenAI/Gemini.
  - Solution is an `autouse` fixture in `conftest.py` patching `_chat` and `openai.OpenAI`.
  - Added clear blueprint for updating `test_api_desktop.py` and `test_api.py` with `auth_headers` and 401 Unauthorized negative tests for `settings`, `monitoring`, and `voice`.

---

## 5. Verification Method

To independently verify these findings:

1. **Android Build Verification**:
   ```bash
   cd android
   .\gradlew.bat assembleDebug --no-daemon
   ```
   *Expected result*: `BUILD SUCCESSFUL` (approx 15-20s).

2. **Git Ignored Status**:
   ```bash
   git ls-files .venv-test/
   ```
   *Expected result*: No output (0 files tracked).

3. **Pytest Benchmark & Mock Verification**:
   - Apply the recommended `autouse` fixture in `tests/conftest.py`.
   - Run:
     ```bash
     pytest --durations=10
     ```
   *Expected result*: All 320+ tests pass in under 10 seconds total.
