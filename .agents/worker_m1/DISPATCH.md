## 2026-08-21T02:31:23Z

You are Worker M1: Pre-Build Test Alignment & Route Fixes.
Working directory: c:\Users\samee\projects\Mimo\.agents\worker_m1\
Identity: Implementation Worker for Pre-Build Test Fixes.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. An auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

MANDATORY INPUTS:
- Read c:\Users\samee\projects\Mimo\.agents\ORIGINAL_REQUEST.md
- Read c:\Users\samee\projects\Mimo\.agents\orchestrator_r5\PROJECT.md
- Read c:\Users\samee\projects\Mimo\.agents\explorer_survey_integration\handoff.md
- Read c:\Users\samee\projects\Mimo\.agents\explorer_survey_android\handoff.md

ASSIGNED TASKS & WRITE OWNERSHIP:
1. File: `api/routes_settings.py`
   Add the missing `@router.get("/openai-test")` route (authenticated with `@Depends(current_user)`):
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
2. Files:
   - `android/app/src/test/java/com/mimo/app/ui/DashboardViewModelTest.kt`
     Implement `override suspend fun sendVoiceCommand(body: VoiceCommandRequest): Map<String, Any>` in `FakeMimoApiService`:
     ```kotlin
     override suspend fun sendVoiceCommand(body: VoiceCommandRequest): Map<String, Any> {
         if (shouldThrowError) throw IOException("Network connection offline")
         return mapOf("status" to "ok")
     }
     ```
   - `android/app/src/test/java/com/mimo/app/ui/DashboardViewModelStressTest.kt`
     Implement `override suspend fun sendVoiceCommand(body: VoiceCommandRequest): Map<String, Any>` in `throwingApiService`:
     ```kotlin
     override suspend fun sendVoiceCommand(body: VoiceCommandRequest): Map<String, Any> {
         throw UnsupportedOperationException()
     }
     ```
3. Verification:
   - Run `pytest tests/` and verify all 423 tests pass in under 30 seconds with zero failures.
   - Run `cmd.exe /c "gradlew.bat testReleaseUnitTest"` inside `android/` and verify all Android unit tests pass cleanly.

OUTPUT REQUIREMENTS:
Write your handoff report to `c:\Users\samee\projects\Mimo\.agents\worker_m1\handoff.md` following the Handoff Protocol (Observation, Logic Chain, Caveats, Conclusion, Verification Method). Maintain progress.md in your working directory.
When complete, notify parent via send_message.
