## 2026-08-20T18:01:43Z

You are worker_m3 (Android Signed Release APK Specialist).
Working directory: c:\Users\samee\projects\Mimo\.agents\worker_m3

Read the authoritative requirements at:
`c:\Users\samee\projects\Mimo\.agents\ORIGINAL_REQUEST.md`

Read survey_explorer_3 survey report at:
`c:\Users\samee\projects\Mimo\.agents\survey_explorer_3\handoff.md`

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your write ownership:
- `android/app/release.keystore`
- `android/app/proguard-rules.pro`
- `android/app/src/main/AndroidManifest.xml`
- `android/app/build.gradle.kts`

Your tasks:
1. Generate release keystore `release.keystore` in `android/app/` using `keytool`:
   `keytool -genkeypair -v -keystore android/app/release.keystore -alias mimo -keyalg RSA -keysize 2048 -validity 10000 -storepass mimo123 -keypass mimo123 -dname "CN=Mimo, OU=Mimo Team, O=Mimo, L=San Francisco, ST=CA, C=US"`
2. Create `android/app/proguard-rules.pro` if missing.
3. Update `android/app/src/main/AndroidManifest.xml` to remove `androidx.work.WorkManagerInitializer` from `androidx.startup.InitializationProvider` as documented in `survey_explorer_3/handoff.md`.
4. Update `android/app/build.gradle.kts` to configure `signingConfigs.release` with `release.keystore` (`storePassword = "mimo123"`, `keyAlias = "mimo"`, `keyPassword = "mimo123"`), assign `signingConfig = signingConfigs.getByName("release")` to `buildTypes.release`, and configure `lint { checkReleaseBuilds = false; abortOnError = false }`.
5. Compile and assemble the signed Release APK:
   `cd android && .\gradlew.bat assembleRelease`
6. Verify output file exists at `android/app/build/outputs/apk/release/app-release.apk`.
7. Verify signature using `apksigner`:
   `& "C:\Users\samee\AppData\Local\Android\Sdk\build-tools\34.0.0\apksigner.bat" verify --verbose "android\app\build\outputs\apk\release\app-release.apk"`
8. Document all steps, configs, and apksigner output in `c:\Users\samee\projects\Mimo\.agents\worker_m3\handoff.md`.
Notify orchestrator when done via `send_message`.
