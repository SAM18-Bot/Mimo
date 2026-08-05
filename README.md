# 🔥 Mimo — AI Accountability System

> A behavior-aware AI productivity coach for students.  
> Real-time screen tracking + computer vision + voice commands + AI roasting.

**Three ways to run Mimo:**
| Mode | Command | Use case |
|---|---|---|
| Server only | `python run_server.py` | Development, browser dashboard |
| Desktop app | `python run_desktop.py` | System tray, native window, notifications — **see [DESKTOP_APP.md](DESKTOP_APP.md)** |
| Packaged app | `python desktop/build.py` then run the built `.exe`/`.app` | Distributing to others, no Python required |

---

## What it does

FocusFire watches what you do, not what you say you'll do.

- **Tracks every app you open** — categorizes it as productive, distracting, or neutral
- **Monitors your physical presence** via ESP32-CAM (are you actually at your desk?)
- **Roasts you in real time** when you spend too long on Instagram or walk away mid-session
- **Manages assignments** with natural language — say "Math assignment due Friday" and it's in the system
- **Generates end-of-day reports** with an AI-powered behavioral analysis
- **Learns your patterns** — finds your peak productive hours, worst days, most avoided subjects
- **Recommends what to study** based on deadlines, subject time gaps, and completion rates

---

## Quick start (no hardware needed)

This gets the server + browser dashboard running. For the full desktop app experience (tray icon, native window, auto-start), see [DESKTOP_APP.md](DESKTOP_APP.md) instead.

```bash
# 1. Unzip and enter
unzip mimo.zip -d mimo && cd mimo

# 2. Virtual environment
python -m venv .venv
source .venv/bin/activate        # Mac/Linux
# .venv\Scripts\activate         # Windows

# 3. Install (no-hardware subset — fast)
pip install fastapi uvicorn sqlalchemy python-dotenv pydantic \
    apscheduler dateparser python-dateutil httpx aiofiles \
    python-multipart openai

# 4. Set your OpenAI key (optional — pre-written roasts work without it)
# nano .env → set OPENAI_API_KEY=sk-...

# 5. Start
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Open **http://localhost:8000** — live dashboard with WebSocket updates.  
Open **http://localhost:8000/docs** — interactive API to inject test data.

---

## Testing without hardware

The system runs fully without ESP32-CAM, microphone, or any hardware.

### Simulate screen events

```bash
# Interactive terminal controller
python mock_screen.py

# Auto-demo cycle (good for showing judges)
python mock_screen.py --demo

# Rapid fire for roast testing
python mock_screen.py --rapid
```

### Simulate camera events

```bash
# Interactive
python mock_cv.py

# Auto-demo
python mock_cv.py --demo
```

### Or use the API directly (http://localhost:8000/docs)

```bash
# Inject a distracting window
curl -X POST http://localhost:8000/screen/mock \
  -H "Content-Type: application/json" \
  -d '{"app": "instagram", "title": "Instagram — Home Feed"}'

# Inject a CV event
curl -X POST http://localhost:8000/cv/mock \
  -H "Content-Type: application/json" \
  -d '{"event": "absent"}'

# Add an assignment
curl -X POST http://localhost:8000/assignments/nlp \
  -H "Content-Type: application/json" \
  -d '{"text": "Math assignment due Friday"}'

# Trigger the roast / EOD report
curl -X POST http://localhost:8000/reports/eod

# Get today's stats
curl http://localhost:8000/reports/stats

# Get behavioral patterns (7-day)
curl http://localhost:8000/reports/patterns

# Get study recommendations
curl http://localhost:8000/study/recommendations
```

---

## Voice commands (when enabled)

Set `NO_VOICE=0` in `.env` and install `pyttsx3 pyaudio SpeechRecognition`.

Say **"hey coach"** → wait for "Yes?" → then:

| Command | Action |
|---|---|
| "Add math assignment due Friday" | Creates assignment |
| "Show my tasks" | Lists upcoming deadlines |
| "How productive was I today" | Reads focus score |
| "What should I study" | StudyAdvisor recommendation |
| "Mark physics done" | Marks assignment complete |
| "Give me my report" | Triggers EOD analysis |

Test voice commands without a microphone via `POST /voice/command`:
```bash
curl -X POST http://localhost:8000/voice/command \
  -H "Content-Type: application/json" \
  -d '{"text": "show my tasks", "speak_response": false}'
```

---

## Dashboard

The live dashboard at **http://localhost:8000** shows:

| Section | What it shows |
|---|---|
| Focus gauge + grade | 0–100 score with A/B/C/D/F letter grade |
| Score verdict | One-line honest assessment of the day |
| Time bars | Productive / distracting / neutral minutes |
| 7-day history | Color-coded bar chart (green=good, red=bad) |
| Day streak | Consecutive days above 50 focus score |
| Behavioral patterns | AI-detected time-of-day trends |
| Current app | Live active window with category glow |
| CV monitor | Presence status from camera |
| Live activity | Rolling log of app switches |
| Assignments | Upcoming deadlines with urgency coloring |
| Study recommendations | AI-generated subject priorities |
| Study plan | Time-blocked schedule based on patterns |
| Roast zone | Live roast feed with animation |

---

## Enabling hardware (ESP32-CAM)

```bash
# 1. Flash esp32/cam_stream.ino via Arduino IDE
#    (set your WiFi credentials in the sketch first)

# 2. Note the IP from Serial Monitor

# 3. Edit .env:
ESP32_STREAM_URL=http://192.168.x.x:81/stream
NO_HARDWARE=0

# 4. Install CV deps:
pip install opencv-python mediapipe

# 5. Restart — camera feed starts automatically
uvicorn main:app --reload
```

---

## API reference

| Method | Path | Description |
|---|---|---|
| GET | `/` | Live dashboard |
| GET | `/health` | System status |
| POST | `/assignments/` | Create assignment |
| POST | `/assignments/nlp` | Create from natural language |
| GET | `/assignments/upcoming` | Due in next N days |
| GET | `/assignments/overdue` | Past due, not done |
| POST | `/assignments/{id}/done` | Mark complete |
| GET | `/screen/sessions` | All tracked sessions |
| GET | `/screen/breakdown` | Productive/distracting breakdown |
| POST | `/screen/mock` | Inject test window event |
| POST | `/cv/mock` | Inject test presence event |
| GET | `/cv/events` | Today's CV event log |
| GET | `/reports/stats` | Today's aggregated stats |
| GET | `/reports/history` | N-day daily summary history |
| GET | `/reports/patterns` | 7-day behavioral patterns |
| GET | `/reports/score/breakdown` | Detailed score components |
| POST | `/reports/eod` | Trigger end-of-day report |
| POST | `/reports/accountability` | Log morning Q&A answer |
| GET | `/study/recommendations` | AI study recommendations |
| GET | `/study/next` | What to study right now |
| GET | `/study/subjects` | Time per subject this week |
| GET | `/schedule/onboarding/questions` | First-run schedule onboarding prompts |
| POST | `/schedule/onboarding` | Build a flexible weekly schedule |
| GET | `/schedule/status` | Schedule setup status |
| GET | `/schedule/weekly` | Active weekly schedule blocks |
| GET | `/schedule/today` | Schedule blocks for a date |
| PATCH | `/schedule/blocks/{id}` | Update schedule block status |
| POST | `/voice/command` | Route voice command (no mic) |
| GET | `/voice/status` | Voice system status |
| GET | `/voice/intents` | All supported command patterns |
| POST | `/auth/register` | Create student or parent account |
| POST | `/auth/login` | Issue account JWT |
| GET | `/auth/me` | Current authenticated account |
| POST | `/devices/register` | Link desktop/Android/hardware device to account |
| GET | `/devices` | List current account devices |
| POST | `/parent/invites` | Student creates parent invite code |
| POST | `/parent/link` | Parent links to student via invite |
| GET | `/parent/children` | Parent lists linked students |
| GET | `/parent/summary/{student_id}` | Parent weekly student summary |
| WS | `/ws` | WebSocket for live dashboard |

---

## Running tests

```bash
pip install pytest pytest-asyncio httpx
python -m pytest tests/ -v
```

169 tests covering: parser, categorizer, scorer, session stitcher, assignments, aggregator, all API routes, and full end-to-end workflows.

---

## Architecture

```
main.py                     ← FastAPI + lifespan startup
├── api/                    ← HTTP + WebSocket route handlers
│   ├── websocket.py        ← event bus (sync→async bridge)
│   └── routes_*.py         ← 6 route modules
├── modules/
│   ├── screen_tracker/     ← cross-platform window poller + SessionStitcher
│   ├── cv_pipeline/        ← ESP32-CAM stream + GazeDetector + presence state machine
│   ├── voice/              ← hotword listener + TTS + intent router
│   ├── assignments/        ← CRUD + NLP parser + ReminderLoop
│   ├── behavior_engine/    ← ProductivityScorer + aggregator + pattern detector
│   └── ai_layer/           ← OpenAI wrapper + roast engine + daily report + study advisor
├── db/                     ← SQLAlchemy models + Alembic migrations
├── schedulers/             ← APScheduler (EOD, Q&A, reminders) + background task manager
├── static/dashboard.html   ← Live WebSocket dashboard
└── esp32/cam_stream.ino    ← Arduino MJPEG stream firmware
```

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | OpenAI key (roasts work without it) |
| `DATABASE_URL` | `sqlite:///./accountability.db` | SQLAlchemy DB URL |
| `ESP32_STREAM_URL` | `http://192.168.1.100:81/stream` | ESP32-CAM MJPEG endpoint |
| `NO_HARDWARE` | `1` | Skip ESP32-CAM and CV pipeline |
| `NO_VOICE` | `1` | Skip microphone and TTS |

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + SQLAlchemy + SQLite |
| Scheduling | APScheduler |
| Screen tracking | psutil + xdotool / win32gui / osascript |
| Computer vision | OpenCV + Mediapipe FaceMesh |
| Voice | SpeechRecognition + pyttsx3 |
| AI | OpenAI GPT-4o-mini (roasts) + GPT-4o (EOD report) |
| Dashboard | Vanilla HTML/CSS/JS + WebSockets |
| Hardware | ESP32-CAM (Arduino) |
| Tests | pytest + FastAPI TestClient |
| Migrations | Alembic |

---

## Hackathon demo sequence (2 minutes)

1. Open dashboard — show live clock, LIVE indicator, green WebSocket dot
2. Type `"Math test due tomorrow"` in quick-add → assignment appears instantly
3. Run `python mock_screen.py --demo` in terminal → watch dashboard respond live
4. Dashboard turns **red** when Instagram fires, **purple** when VS Code fires
5. Wait ~10s for roast to appear in the Roast Zone at the bottom
6. Hit `POST /reports/eod` in /docs → AI report generates, roast appears
7. Show `/reports/patterns` → "You are most productive between 9 AM and 11 AM"
8. Show `/study/recommendations` → personalized study priorities

**The hook:** "Other tools track time. This one watches your behavior and calls you out."

---

*Built with FastAPI · Mediapipe · OpenAI · ESP32-CAM*  
*6,900+ lines across 73 files · 169 passing tests*
