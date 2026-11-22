# 🚀 Mimo Full-Stack Deployment Guide

This guide provides the exact file locations and commands you need to deploy all three components of the Mimo ecosystem: the **Cloud Backend**, the **Desktop App**, and the **Android App**.

---

## 1. ☁️ The Cloud Backend (FastAPI + PostgreSQL)

The backend acts as the central brain. It receives data from the desktop and mobile apps, runs the AI processing, and serves the web dashboard.

### **Deploying Locally (For Testing)**
You can run the entire backend + database on your own machine using Docker.
- **File Locations:** 
  - `[Mimo Root]/Dockerfile`
  - `[Mimo Root]/docker-compose.yml`
- **Commands:**
  ```bash
  # From the checkout, set SECRET_KEY and JWT_SECRET_KEY in .env.
  docker-compose up --build -d
  ```
- **Result:** The backend is now live at `http://localhost:8000`.

### **Deploying with Neon (Database) + Render (Backend) - 100% FREE**
Use a persistent Neon database and a Docker web service connected to this repository.
Set these variables under the Render service's Environment tab.

- `DATABASE_URL` holds the Neon connection string. Mimo accepts the PostgreSQL URL schemes and requires TLS for Neon hosts.
- `SECRET_KEY` holds the Fernet key used to encrypt personal API keys. Preserve the existing private key across deploys. For a new installation generate it once with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
- `JWT_SECRET_KEY` holds a persistent random signing secret. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
- `GEMINI_API_KEY` enables live coaching, and `GOOGLE_CLIENT_ID` enables Google sign-in.

Leave Render's Docker start command empty and set the health check path to `/health`. The image runs Alembic before serving traffic. Take a database backup before the first upgrade. Startup recognizes the previous unversioned ORM schema. A schema mismatch stops the upgrade so the operator can reconcile a backup with revision 005. A cold service may take up to a minute to answer the first request.

---

## 2. 💻 The Desktop App (Windows .exe)

The desktop app runs locally on your PC. It tracks your screen, forcefully kills distracting apps, and pushes the data to the cloud backend.

- **File Location:** 
  - `[Mimo Root]/desktop/build.py`
  - *This script generates the standalone executable.*
- **Commands:**
  ```bash
  # Ensure you are in the root directory
  cd c:\Users\samee\projects\Mimo

  python desktop/build.py
  ```
- The Windows workflow uploads the complete `dist/Mimo/` directory. Extract the artifact and run `Mimo.exe` beside its bundled libraries. Set `MIMO_CLOUD_URL` on the client to override the default server at runtime.

---

## 3. 📱 The Android App (.apk)

The mobile app serves as a companion dashboard and pushes mobile tracking events to the central backend.

- **File Location:** 
  - `[Mimo Root]/android/`
  - *This is a native Kotlin Jetpack Compose project.*
- **Commands:**
  ```bash
  # Navigate into the android folder
  cd c:\Users\samee\projects\Mimo\android

  # Build the shareable Debug APK
  gradlew assembleDebug
  ```
- **Result:** The compiled Android app will be located at:
  `c:\Users\samee\projects\Mimo\android\app\build\outputs\apk\debug\app-debug.apk`
- **Installation:** You can transfer this `.apk` file to your Android phone via Google Drive or USB, tap it, and hit "Install".

The Android workflow uploads the debug APK on push. For a signed release, store the base64-encoded private upload keystore in the GitHub Actions secret `ANDROID_KEYSTORE_BASE64`, alongside `KEYSTORE_PASSWORD`, `KEY_ALIAS`, and `KEY_PASSWORD`. Reuse the signing identity for existing installations. Run the Android workflow manually on `main` with **Build a signed release APK** selected. CI verifies the APK signature before uploading the artifact.

Android study-block enforcement uses notifications. It requires notification permission, and usage tracking requires the student's Usage Access grant.
5. Profit!
