# FocusFire — Setup, Run & Test Guide
### No hardware needed for this guide. ESP32-CAM added later.

---

## Step 1 — Install Python

You need **Python 3.10 or higher**.

Check what you have:
```bash
python --version
# or
python3 --version
```

If you don't have it: download from https://www.python.org/downloads/  
Windows users: during install, tick **"Add Python to PATH"**.

---

## Step 2 — Unzip the project

```bash
unzip focusfire.zip -d focusfire
cd focusfire
```

---

## Step 3 — Create a virtual environment

This keeps all packages isolated from your system Python.

**Windows (cmd or PowerShell):**
```cmd
python -m venv .venv
.venv\Scripts\activate
```

**Mac / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

You should see `(.venv)` in your terminal prompt. If you close the terminal, run the activate command again before starting the server.

---

## Step 4 — Install dependencies

```bash
pip install fastapi uvicorn sqlalchemy python-dotenv pydantic apscheduler dateparser python-dateutil httpx aiofiles python-multipart openai
```

This is the **no-hardware subset** — no OpenCV, Mediapipe, PyAudio needed yet.  
Full install (for later, when adding hardware):
```bash
pip install -r requirements.txt
```

---

## Step 5 — Configure your .env file

The `.env` file was already created for you. Open it:

```
OPENAI_API_KEY=sk-your-key-here
DATABASE_URL=sqlite:///./accountability.db
ESP32_STREAM_URL=http://192.168.1.100:81/stream
NO_HARDWARE=1
NO_VOICE=1
```

**What to change:**
- `OPENAI_API_KEY` — paste your actual key from https://platform.openai.com/api-keys  
  (Leave as fake key to test without AI — pre-written roasts still fire)
- `NO_HARDWARE=1` — keep this. Disables ESP32-CAM entirely.
- `NO_VOICE=1` — keep this. Disables microphone. Roasts print to console instead.
- `ESP32_STREAM_URL` — ignore for now.

---

## Step 6 — Start the server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

You should see:
```
INFO:     AI Accountability System starting...
INFO:     NO_HARDWARE=1 — Camera/CV disabled. Use POST /cv/mock to inject events.
INFO:     NO_VOICE=1 — Voice listener disabled.
INFO:     Screen tracker started.
INFO:     Roast engine ready.
INFO:     Dashboard → http://localhost:8000
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Open your browser: **http://localhost:8000**

---

## Step 7 — Test everything

Open three things side by side:
1. **Dashboard** → http://localhost:8000
2. **API docs** → http://localhost:8000/docs  ← this is how you inject test data
3. **Terminal** ← watch logs here

---

### Test A — Add assignments (via dashboard)

In the dashboard, bottom of the right column, type into the quick-add box:
```
Math assignment due Friday
```
Press Enter or click **+ Add**.

More examples to try:
```
Physics lab due next Monday
AI project due tomorrow
DBMS homework due in 3 days
CS assignment due June 20
```

Watch the assignment list update in real time.

---

### Test B — Inject a window change (simulate app switching)

Go to http://localhost:8000/docs → scroll to **POST /screen/mock** → click **Try it out**

Paste this body and click Execute:
```json
{
  "app": "instagram",
  "title": "Instagram — Home"
}
```

Watch the dashboard center panel update: the app name changes to "instagram" with a **red glow** and badge that says **DISTRACTING**.

Try a productive one:
```json
{
  "app": "code",
  "title": "main.py — FocusFire"
}
```
Dashboard turns **purple** with **PRODUCTIVE** badge.

---

### Test C — Trigger a roast manually

In **/docs** → **POST /screen/mock** — inject instagram and keep clicking it.

The roast engine fires after 5 minutes of consecutive distraction on a distracting app. For demo/testing, temporarily lower the threshold by editing `.env`:
```
# Add this line to .env to roast after 0.1 minutes (6 seconds) for testing
```

OR test the roast directly in /docs → **POST /reports/eod** to generate a full end-of-day report and roast.

Easier option — run the mock CV script in a second terminal:
```bash
python mock_cv.py --demo
```

---

### Test D — CV presence (no camera)

In **/docs** → **POST /cv/mock**

```json
{ "event": "present" }
```
Dashboard shows: 🟢 **Present — focused**

```json
{ "event": "absent" }
```
Dashboard shows: 🔴 **Away from desk**

```json
{ "event": "distracted" }
```
Dashboard shows: 🟡 **Looking away**

Or use the interactive mock script:
```bash
# In a second terminal (with venv activated)
python mock_cv.py

# Then type:
# p → present
# a → absent  
# d → distracted
# r → returned
# q → quit
```

---

### Test E — EOD report (end-of-day analysis)

In **/docs** → **POST /reports/eod** → Execute

This triggers the full report pipeline:
- Aggregates today's screen time and CV events from the DB
- Calls OpenAI (if key is set) to generate analysis and roast
- Speaks via TTS (if NO_VOICE=0) or prints to console
- Broadcasts to dashboard

The roast from the AI report will appear in the **Roast Zone** at the bottom of the dashboard.

---

### Test F — Full stats

In **/docs** → **GET /reports/stats** — see your today's computed stats.

Or directly: http://localhost:8000/reports/stats

Sample output:
```json
{
  "focus_score": 76.9,
  "productive_min": 90,
  "distracting_min": 15,
  "productive_apps": "code (60m), chrome (30m)",
  "distracting_apps": "instagram (15m)",
  "upcoming_list": ["Math due 2026-06-12"]
}
```

---

### Test G — Morning accountability Q&A

In **/docs** → **POST /reports/accountability**

```json
{
  "question": "What is your main priority today?",
  "answer": "Finish the AI project report and start DSA revision"
}
```

These answers get pulled into the EOD report for context.

---

## Full demo sequence (for hackathon judges)

Run this exact sequence in 2 minutes:

**Step 1** — Open dashboard. Show it's live with the clock ticking.

**Step 2** — Type in the quick-add box: `"Math test due tomorrow"`. Show it appears instantly.

**Step 3** — Go to /docs, inject window change to `instagram`. Show the red glow appear on the dashboard in real time.

**Step 4** — Inject window change to `code`. Show it go green.

**Step 5** — Inject instagram again, then click EOD report trigger. Show the roast appear in the Roast Zone.

**Step 6** — Show the focus score gauge animate as you inject different sessions.

---

## Enabling features one at a time

### Enable real screen tracking (detects your actual apps)

No extra setup needed — it's already running. The server tracks your active window in real time.

On **Linux**, you need `xdotool`:
```bash
sudo apt install xdotool
```

On **Windows**, install pywin32:
```bash
pip install pywin32
```

### Enable real OpenAI roasts

1. Get a key: https://platform.openai.com/api-keys
2. Edit `.env`: `OPENAI_API_KEY=sk-your-real-key`
3. Restart the server
4. Roasts will now be AI-generated and reference your actual data

### Enable voice commands (microphone)

1. Set `NO_VOICE=0` in `.env`
2. Install voice deps:
   ```bash
   pip install SpeechRecognition pyttsx3 pyaudio
   # Linux also needs:
   sudo apt install espeak portaudio19-dev
   ```
3. Restart server
4. Say **"hey coach"** → wait for "Yes?" → say your command
5. Commands: "add assignment", "show tasks", "how productive was I", "what should I study"

### Enable ESP32-CAM

1. Flash `esp32/cam_stream.ino` via Arduino IDE
2. Set your WiFi credentials in the sketch
3. Note the IP from Serial Monitor
4. Set in `.env`: `ESP32_STREAM_URL=http://<IP>:81/stream`
5. Set `NO_HARDWARE=0` in `.env`
6. Install CV deps:
   ```bash
   pip install opencv-python mediapipe
   ```
7. Restart server. The camera feed starts automatically.

---

## Common errors and fixes

**"ModuleNotFoundError: No module named 'X'"**  
→ You're not in the virtual environment. Run:  
`source .venv/bin/activate` (Mac/Linux) or `.venv\Scripts\activate` (Windows)

**Dashboard shows "Reconnecting..." in top right**  
→ Server isn't running. Start it: `uvicorn main:app --port 8000 --reload`

**Screen tracker shows "unknown" for every app**  
→ On Linux, install xdotool: `sudo apt install xdotool`  
→ On Windows, install pywin32: `pip install pywin32`

**Roasts not firing**  
→ Default threshold is 5 minutes on a distracting app. Use /docs to inject window events or trigger EOD report manually.

**"cannot import name X" errors**  
→ Run `pip install -r requirements.txt` to make sure all packages are installed.

**Port 8000 already in use**  
→ Change port: `uvicorn main:app --port 8001 --reload`

---

## File map (where everything lives)

```
focusfire/
├── main.py                    ← start here — the app entry point
├── config.py                  ← all settings and thresholds
├── .env                       ← your API key and flags
├── mock_cv.py                 ← run this to simulate the camera
│
├── api/
│   ├── routes_assignments.py  ← POST /assignments/nlp  (quick add)
│   ├── routes_screen.py       ← POST /screen/mock      (inject window)
│   ├── routes_cv.py           ← POST /cv/mock          (inject presence)
│   ├── routes_reports.py      ← GET  /reports/stats    (today's numbers)
│   └── websocket.py           ← real-time event bus
│
├── modules/
│   ├── screen_tracker/        ← watches your active window
│   ├── cv_pipeline/           ← ESP32-CAM + Mediapipe
│   ├── voice/                 ← "hey coach" hotword + TTS
│   ├── assignments/           ← CRUD + date parsing
│   ├── behavior_engine/       ← focus score, patterns
│   └── ai_layer/              ← roast engine + EOD report
│
├── schedulers/
│   ├── background_tasks.py    ← starts all threads
│   └── daily_trigger.py       ← 10PM report, 15min reminders
│
├── static/
│   └── dashboard.html         ← the live WebSocket dashboard
│
├── db/
│   ├── models.py              ← 8 database tables
│   └── database.py            ← SQLAlchemy setup
│
└── esp32/
    └── cam_stream.ino         ← Arduino firmware (flash later)
```
