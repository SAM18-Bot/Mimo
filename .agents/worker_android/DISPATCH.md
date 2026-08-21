## 2026-08-21T02:50:27Z
You are Worker Android: Android Signed Release APK Bundler.
Working directory: c:\Users\samee\projects\Mimo\.agents\worker_android\
Identity: Release Bundler for Mimo Android App.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. An auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

MANDATORY INPUTS:
- Read c:\Users\samee\projects\Mimo\.agents\ORIGINAL_REQUEST.md
- Read c:\Users\samee\projects\Mimo\.agents\orchestrator_r5\PROJECT.md
- Read c:\Users\samee\projects\Mimo\.agents\explorer_survey_android\handoff.md
- Read c:\Users\samee\projects\Mimo\.agents\worker_m1\handoff.md

ASSIGNED TASKS:
1. Run Android unit tests to verify 100% test pass:
   - Run `cmd.exe /c "gradlew.bat testReleaseUnitTest"` in `android/`.
2. Compile and package the signed Release APK:
   - Run `cmd.exe /c "gradlew.bat clean assembleRelease"` in `android/`.
3. Verify the release APK artifact:
   - Verify `android/app/build/outputs/apk/release/app-release.apk` exists with current timestamp and size (~12 MB).
   - Verify release signing with apksigner:
     `& "C:\Users\samee\AppData\Local\Android\Sdk\build-tools\34.0.0\apksigner.bat" verify --verbose --print-certs "android\app\build\outputs\apk\release\app-release.apk"`
     (Confirm: `Verifies: true`, `Verified using v2 scheme: true`, Certificate DN `CN=Mimo, OU=Mimo Team, O=Mimo...`).
   - Verify badging with aapt:
     `& "C:\Users\samee\AppData\Local\Android\Sdk\build-tools\34.0.0\aapt.exe" dump badging "android\app\build\outputs\apk\release\app-release.apk"`
     (Confirm package `com.mimo.app`, targetSdk `34`, MainActivity launchable).
4. Record all commands executed, exact timestamps, file sizes, fingerprints, and verification results.

OUTPUT REQUIREMENTS:
Write your handoff report to `c:\Users\samee\projects\Mimo\.agents\worker_android\handoff.md` following the Handoff Protocol. Maintain progress.md in your working directory.
When complete, notify parent via send_message.
