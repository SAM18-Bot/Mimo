## 2026-08-11T03:01:28Z
You are worker_m2 (Requirement R2 Desktop Build Worker).
Your working directory is: c:\Users\samee\projects\Mimo\.agents\work_m2
Read `c:\Users\samee\projects\Mimo\.agents\ORIGINAL_REQUEST.md` and `c:\Users\samee\projects\Mimo\.agents\orchestrator_r3\PROJECT.md`.
Also check survey analysis at `c:\Users\samee\projects\Mimo\.agents\teamwork_preview_explorer_survey_2\analysis.md`.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Tasks:
1. Update `desktop/mimo.spec`: remove `"numpy"` from `excludes` list (line 126) so OpenCV/CV modules will not crash at runtime.
2. Fix zombie process hazards in `desktop/main_desktop.py` and `desktop/tray.py`:
   - In `desktop/tray.py`, update `_on_quit` so it calls `_shutdown()` (or equivalent cleanup) before calling `os._exit(0)`.
   - In `desktop/main_desktop.py`, ensure the main thread loop exits cleanly when the application or tray is closed.
3. Build the desktop executable using PyInstaller: `pyinstaller desktop/mimo.spec`.
4. Verify that `dist/Mimo/Mimo.exe` binary exists.
5. Verify that `dist/Mimo/_internal/static/` (or `dist/Mimo/static/`) contains static HTML files (`dashboard.html`, etc.).
6. Test launching `dist/Mimo/Mimo.exe` briefly to confirm clean startup and non-zombie shutdown.
7. Save build logs and verification report to `c:\Users\samee\projects\Mimo\.agents\work_m2\build_log.txt`.
8. Write handoff report to `c:\Users\samee\projects\Mimo\.agents\work_m2\handoff.md`.
9. Send a message to parent when finished.
