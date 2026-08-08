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
  # Ensure you are in the root directory
  cd c:\Users\samee\projects\Mimo

  # Build and start the containers in the background
  docker-compose up --build -d
  ```
- **Result:** The backend is now live at `http://localhost:8000`.

### **Deploying with Neon (Database) + Render (Backend) - 100% FREE**
If you don't have a credit card for Oracle, the best permanent free stack is to host the database on Neon (which never expires and requires no card) and the backend on Render.

#### Step A: Set up the Database (Neon)
1. Go to [neon.tech](https://neon.tech/) and sign up (no credit card required).
2. Create a new Postgres project.
3. Once created, click on your Dashboard and copy the **Postgres Connection String** (it starts with `postgresql://`).

#### Step B: Set up the Backend (Render)
1. **Upload your code to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git push -u origin main
   ```
2. **Deploy on Render (render.com):**
   - Create a new **Web Service** and connect your GitHub repo.
   - **Environment:** Docker
   - **Build Command:** (Leave blank, Render detects the `Dockerfile` automatically)
   - **Start Command:** (Leave blank)
   - Add Environment Variables:
     - `DATABASE_URL` = (Paste your Neon Postgres Connection String here)
     - `OPENAI_API_KEY` = (Your OpenAI Key)
     - `GEMINI_API_KEY` = (Your Gemini Key)
     - `NO_HARDWARE` = `1`
     - `NO_TRACKER` = `1`
3. Click **Deploy**.

> [!IMPORTANT]
> Once deployed, Render will give you a public URL (e.g., `https://mimo-app.onrender.com`). You **MUST** use this URL when configuring your Desktop and Android apps!

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

  # If deploying to the cloud, set the cloud URL first so the .exe knows where to send data
  # (If testing locally, you can skip this step)
  set MIMO_CLOUD_URL=https://mimo-app.onrender.com

  # Build the .exe
  python desktop/build.py
  ```
- **Result:** You will find `MimoDesktopTracker.exe` inside the `dist/` folder. You can email this `.exe` to anyone or put it on a USB drive. When they run it, it will silently track them and sync data to your cloud URL!

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

---

## 🎯 Summary Checklist for the Hackathon Demo
1. Run `docker-compose up -d` to start the backend.
2. Open `http://localhost:8000` in your browser to show the Dashboard.
3. Double click `dist/MimoDesktopTracker.exe` to start the desktop tracker.
4. Show the Android app running on an emulator or physical device.
5. Profit!
