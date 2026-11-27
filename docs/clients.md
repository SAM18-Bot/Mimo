# Windows and Android clients

For prebuilt files, sign in to GitHub and follow [Downloads](../README.md#downloads). Both clients use the same student account when they point to the same Mimo server.

## Windows

Extract the whole `Mimo-Windows` artifact into one folder and open `Mimo.exe`. Keep the executable next to its bundled libraries. The app opens the dashboard and runs a tray tracker. During a scheduled study block, the tracker can close a distracting process after its configured time limit.

The client defaults to the hosted Mimo service. To use your own deployment, set the server origin before launching the executable.

```powershell
$env:MIMO_CLOUD_URL = "https://mimo.example.com"
.\Mimo.exe
```

Use `$env:MIMO_CLOUD_URL = "local"` to launch the bundled service on the same computer. The local mode can run with camera and voice disabled. The tray provides a **Quit** action for a full shutdown.

### Build from source on Windows

From the repository root, use Python 3.11 and a virtual environment.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements_desktop.txt
.\.venv\Scripts\python.exe desktop/build.py
.\.venv\Scripts\python.exe scripts/check_desktop_bundle.py dist/Mimo/Mimo.exe
```

Distribute the complete `dist/Mimo/` directory. To run the desktop app from the checkout, use `python run_desktop.py` in the same environment. The [Windows workflow](../.github/workflows/desktop.yml) builds the bundle on a Windows runner and checks its local server and pages.

## Android

The native app supports Android 8.0 and later. Extract the Android debug artifact and tap `app-debug.apk` on the phone. To use your own backend, choose **Change server** on the sign-in screen and enter an HTTPS origin.

Usage Access enables app-usage tracking. Notification permission enables study reminders on Android versions that request it. Students can continue into the app without granting either permission. A parent account opens the parent view and uses a student invite code to link the accounts.

### Build from source

Use JDK 17 and Android SDK Platform 34. Open the [android/](../android/) directory in Android Studio or use its checked-in Gradle wrapper.

```bash
cd android
./gradlew assembleDebug testDebugUnitTest lintDebug
```

On Windows, use `gradlew.bat`. The debug APK is at `android/app/build/outputs/apk/debug/app-debug.apk`.

### Signed Android release

The [Android workflow](../.github/workflows/android.yml) can build a signed APK when the repository has the existing release keystore and credentials configured in Actions secrets. It reads `ANDROID_KEYSTORE_BASE64`, `KEYSTORE_PASSWORD`, `KEY_ALIAS` and `KEY_PASSWORD`. Run the workflow manually on `main` with **Build a signed release APK** selected. The workflow verifies the signature and uploads `Mimo-Android-release`. Updates to an installed release must use its original signing identity.
