# 🔥 Mimo — AI Student Accountability System

> A behavior-aware AI productivity coach for students.  
> Real-time screen tracking + computer vision + AI roasting + Strict App Blocking.

**Mimo watches what you do, not what you say you'll do.**

---

## 🚀 Killer Features

- **Strict App Blocking:** If you spend > 10 minutes on Instagram during a scheduled Study Block, Mimo *force kills* the process (`taskkill` / `killall`).
- **Productivity Pet (Tamagotchi):** A digital pet on your web dashboard gets hyped (🚀) when you focus, and angry (😡) when you get distracted!
- **Multi-LLM Support:** Native support for both **Google Gemini 2.5 Flash** and **OpenAI GPT-4o**.
- **Offline-Caching Desktop App:** The standalone `.exe` caches data locally when offline and pushes to the cloud when the internet reconnects.
- **Physical Presence Detection:** Optional hardware integration via ESP32-CAM (are you actually at your desk?).

---

## ☁️ Quick Start (Cloud Deployment)

Mimo is built to be deployed instantly using Docker. It natively connects to PostgreSQL and runs headlessly (no local webcam/tracking needed on the server).

```bash
# 1. Provide an AI key in .env (either GEMINI_API_KEY or OPENAI_API_KEY)
echo "GEMINI_API_KEY=your_key_here" > .env

# 2. Spin up the FastAPI backend and Postgres Database
docker-compose up --build -d
```

Open **http://localhost:8000** for the live dashboard!

---

## 💻 Desktop Client (.exe)

To track your screen, compile the standalone Python executable. This client runs silently, tracks your active window, and aggressively terminates distracting apps!

```bash
python desktop/build.py
```
This generates `dist/MimoDesktopTracker.exe`. Run it and it will push data to your cloud dashboard.

---

## 📱 Mobile Companion App (.apk)

Mimo comes with a native Kotlin Android application that syncs with your central dashboard!
```bash
cd android
./gradlew assembleRelease
```
Install the generated `.apk` on your phone to track mobile app usage.

---

## 🕹️ Hackathon Demo Sequence (2 minutes)

1. Open dashboard — point out the live **Productivity Pet** sleeping (😴).
2. Type `"Math test due tomorrow"` in quick-add → assignment appears instantly.
3. Run `python mock_screen.py --demo` in terminal to simulate a user sitting down to study.
4. Dashboard turns **purple**, and the Pet gets HYPED (🚀).
5. Suddenly, the user opens Instagram... wait 10 seconds.
6. The dashboard turns **red**, the Pet gets ANGRY (😡), and an AI Roast appears in the Roast Zone!
7. Point out that if they stayed on Instagram for 10 minutes, the Desktop Client would forcefully kill the app process.
8. Show `/reports/patterns` to prove it learns time-of-day trends.

**The hook:** "Other tools track time. Mimo watches your behavior, roasts you, and forcibly blocks your distractions."

---

*Built with FastAPI · PostgreSQL · Google Gemini · Docker · Jetpack Compose*
