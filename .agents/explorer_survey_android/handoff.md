# Survey Report: Android Build & Signed Release APK Setup

## 1. Observation

### 1.1 Project Structure and Build Layout
- **Root Directory**: `android/`
  - `build.gradle.kts`: Configures Android Gradle Plugin (`com.android.application:8.2.2`), Kotlin (`org.jetbrains.kotlin.android:1.9.22`), and Kapt (`org.jetbrains.kotlin.kapt:1.9.22`).
  - `settings.gradle.kts`: Declares `rootProject.name = "Mimo"`, includes module `:app`, and configures repositories `google()`, `mavenCentral()`, and `gradlePluginPortal()`.
  - `gradle.properties`: Configures `android.useAndroidX=true`, `android.enableJetifier=true`, `org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8`.
  - `local.properties`: Defines `sdk.dir=C\:\\Users\\samee\\AppData\\Local\\Android\\Sdk`.
  - `gradlew` / `gradlew.bat`: Gradle wrapper version `8.5` (`distributionUrl=https\://services.gradle.org/distributions/gradle-8.5-bin.zip`).

### 1.2 Module Configuration (`android/app/build.gradle.kts`)
- **SDK Target**: `compileSdk = 34`, `targetSdk = 34`, `minSdk = 26`.
- **Application ID & Versioning**: `applicationId = "com.mimo.app"`, `versionCode = 1`, `versionName = "1.0"`.
- **Java / Kotlin Compatibility**: `JavaVersion.VERSION_1_8`, `jvmTarget = "1.8"`.
- **Jetpack Compose**: Enabled with `kotlinCompilerExtensionVersion = "1.5.8"`, BOM `2024.02.00`.
- **Key Dependencies**:
  - `androidx.core:core-ktx:1.12.0`, `lifecycle-runtime-ktx:2.7.0`, `activity-compose:1.8.2`
  - Retrofit `2.9.0`, OkHttp `4.12.0`, Gson `2.10.1`
  - Room `2.6.1` with `kapt`
  - WorkManager `2.9.0`
  - Google Identity Credential Manager `1.2.1`

### 1.3 Keystore and Release Signing Configuration
- **Keystore File Location**: `android/app/release.keystore` (verified present on disk).
- **Gradle Signing Configuration** (`android/app/build.gradle.kts:24-42`):
  ```kotlin
  signingConfigs {
      create("release") {
          storeFile = file("release.keystore")
          storePassword = "mimo123"
          keyAlias = "mimo"
          keyPassword = "mimo123"
      }
  }

  buildTypes {
      release {
          signingConfig = signingConfigs.getByName("release")
          isMinifyEnabled = false
          proguardFiles(
              getDefaultProguardFile("proguard-android-optimize.txt"),
              "proguard-rules.pro"
          )
      }
  }
  ```
- **Keystore Inspection via `keytool` & `gradlew signingReport`**:
  - Store Type: `PKCS12`
  - Key Alias: `mimo`
  - Key Algorithm: `2048-bit RSA`
  - Signature Algorithm: `SHA256withRSA`
  - Validity: `Thu Aug 20 23:32:14 IST 2026` until `Mon Jan 05 23:32:14 IST 2054`
  - Owner / Issuer: `CN=Mimo, OU=Mimo Team, O=Mimo, L=San Francisco, ST=CA, C=US`
  - SHA-1 Fingerprint: `23:7F:0F:9B:B8:1B:50:6B:8A:BE:D9:6E:42:97:02:CF:AE:D7:9A:2A`
  - SHA-256 Fingerprint: `1F:69:8C:E5:EF:DF:27:C5:62:55:C6:14:96:13:1C:5B:CE:C4:85:A1:B4:65:8D:6C:22:AC:5C:34:91:9B:0F:D2`

### 1.4 Release Build Execution and APK Output
- Command executed: `cmd.exe /c "gradlew.bat assembleRelease"` from `android/`.
- Status: `BUILD SUCCESSFUL in 40s` (41 actionable tasks executed / up-to-date).
- **Target Output APK**: `c:\Users\samee\projects\Mimo\android\app\build\outputs\apk\release\app-release.apk`
- File Size: `12,278,172` bytes (~12.3 MB).
- **Signature Verification via `apksigner.bat verify --verbose --print-certs`**:
  - `Verifies: true`
  - `Verified using v2 scheme (APK Signature Scheme v2): true`
  - Signer SHA-256 Digest: `1f698ce5efdf27c56255c61496131c5bcec485a1b4658d6c22ac5c34919b0fd2` (matches `release.keystore`).

### 1.5 Recent Source Code Updates Packaged
- `android/app/src/main/java/com/mimo/app/data/TokenManager.kt`: Encapsulates JWT storage and onboarding completion status.
- `android/app/src/main/java/com/mimo/app/network/WebSocketManager.kt`: Accepts `token: String?` and dynamically formats WebSocket URL to `wss://mimo-e8u2.onrender.com/ws?token=<token>`.
- `android/app/src/main/java/com/mimo/app/network/ApiClient.kt`: Integrates OkHttp interceptor injecting `Authorization: Bearer <token>` retrieved from `TokenManager`.
- `android/app/src/main/java/com/mimo/app/network/MimoApiService.kt`: Defines API endpoints including newly added `POST /voice/command` (`sendVoiceCommand`).
- `android/app/src/main/java/com/mimo/app/ui/DashboardViewModel.kt`: Connects WebSocket passing real token `TokenManager.getToken(application)`, and implements `sendVoiceCommand`.
- `android/app/src/main/java/com/mimo/app/service/RoastEnforcementService.kt`: Connects WebSocket with `TokenManager.getToken(this)` in foreground service to trigger roast notifications.

### 1.6 Identified Issue in Unit Tests
- When running `gradlew.bat test` or `gradlew.bat testDebugUnitTest`, Kotlin compilation fails at task `:app:compileDebugUnitTestKotlin` / `:app:compileReleaseUnitTestKotlin`:
  1. `DashboardViewModelStressTest.kt:171:34`: Object does not implement abstract member `public abstract suspend fun sendVoiceCommand(body: VoiceCommandRequest): Map<String, Any>`.
  2. `DashboardViewModelTest.kt:21:1`: Class `FakeMimoApiService` does not implement abstract member `public abstract suspend fun sendVoiceCommand(body: VoiceCommandRequest): Map<String, Any>`.

---

## 2. Logic Chain

1. **Gradle Build Health**: AGP 8.2.2 + Kotlin 1.9.22 + Gradle 8.5 with Java 17 (OpenJDK 17.0.20) compiles the production release app cleanly without any missing symbols or dependencies.
2. **Release Signing Validity**: `signingConfigs.release` in `android/app/build.gradle.kts` points to `release.keystore` using alias `mimo` and password `mimo123`. Both `keytool` and `gradlew signingReport` confirm that the keystore is valid until 2054. `apksigner` verifies that `app-release.apk` is signed with v2 scheme using this certificate.
3. **Artifact Production**: Running `.\gradlew.bat assembleRelease` generates the signed release APK at `android/app/build/outputs/apk/release/app-release.apk`.
4. **Test Suite Resolution**: The unit test compile failure does not block `assembleRelease` (which compiles only main source sets and packages the release variant), but blocks `./gradlew.bat test`. Implementing `sendVoiceCommand` in both mock/fake test classes will restore complete unit test pass capability.

---

## 3. Caveats

- **Network Runtime Dependency**: The app's `baseUrl` points to `https://mimo-e8u2.onrender.com/` and WebSocket points to `wss://mimo-e8u2.onrender.com/ws`. When building offline, Gradle dependencies must already be cached in Gradle/Maven cache (which they currently are).
- **ProGuard / Minification**: `isMinifyEnabled = false` is currently configured for release builds in `build.gradle.kts`. If code obfuscation/shrinking is enabled in the future, ProGuard keep rules in `proguard-rules.pro` will need validation for Room, Retrofit, and Gson models.

---

## 4. Conclusion

- The Android project is fully configured and ready for building signed Release APKs.
- Existing keystore credentials (`android/app/release.keystore`, alias `mimo`, password `mimo123`) are valid, active, and properly wired into the Gradle release build type.
- The build command is `cmd.exe /c "gradlew.bat assembleRelease"` (or `.\gradlew.bat assembleRelease` from `android/`), producing `android/app/build/outputs/apk/release/app-release.apk`.
- To allow `./gradlew.bat test` to pass, add the missing `sendVoiceCommand` method to `FakeMimoApiService` in `DashboardViewModelTest.kt` and `throwingApiService` in `DashboardViewModelStressTest.kt`.

### Proposed Fix for Test Mock Classes:
In `android/app/src/test/java/com/mimo/app/ui/DashboardViewModelTest.kt`:
```kotlin
override suspend fun sendVoiceCommand(body: VoiceCommandRequest): Map<String, Any> {
    if (shouldThrowError) throw IOException("Network connection offline")
    return mapOf("status" to "ok")
}
```
In `android/app/src/test/java/com/mimo/app/ui/DashboardViewModelStressTest.kt`:
```kotlin
override suspend fun sendVoiceCommand(body: VoiceCommandRequest): Map<String, Any> {
    throw UnsupportedOperationException()
}
```

---

## 5. Verification Method

### Step 1: Clean & Build Release APK
```powershell
cd c:\Users\samee\projects\Mimo\android
.\gradlew.bat clean assembleRelease
```
Expected: `BUILD SUCCESSFUL` and file `android\app\build\outputs\apk\release\app-release.apk` created.

### Step 2: Verify APK Signature Scheme and Fingerprints
```powershell
& "C:\Users\samee\AppData\Local\Android\Sdk\build-tools\34.0.0\apksigner.bat" verify --verbose --print-certs "c:\Users\samee\projects\Mimo\android\app\build\outputs\apk\release\app-release.apk"
```
Expected: `Verifies`, `Verified using v2 scheme: true`, SHA-256 `1f698ce5efdf27c56255c61496131c5bcec485a1b4658d6c22ac5c34919b0fd2`.

### Step 3: Verify Gradle Signing Report
```powershell
cd c:\Users\samee\projects\Mimo\android
.\gradlew.bat signingReport
```
Expected: Variant `release` configured with `release.keystore` and alias `mimo`.

### Step 4: Run Unit Tests (after applying proposed mock fix)
```powershell
cd c:\Users\samee\projects\Mimo\android
.\gradlew.bat test
```
Expected: `BUILD SUCCESSFUL`, all unit tests pass.
