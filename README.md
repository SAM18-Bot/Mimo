<div align="center">
  <img src="https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/shield-check.svg" width="80" alt="Mimo Logo" />
  <h1>Mimo</h1>
  <p><b>An intelligent, behavior-aware accountability system and strict screen-time enforcer.</b></p>
  
  <p>
    <a href="#features">Features</a> •
    <a href="#installation">Installation</a> •
    <a href="#architecture">Architecture</a> •
    <a href="#contributing">Contributing</a>
  </p>

  <p>
    <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python Version">
    <img src="https://img.shields.io/badge/FastAPI-0.111.0-009688.svg" alt="FastAPI">
    <img src="https://img.shields.io/badge/Kotlin-Android-green.svg" alt="Android Support">
    <img src="https://img.shields.io/badge/License-MIT-gray.svg" alt="License">
  </p>
</div>

---

## Overview

Mimo is an aggressive productivity tracker that goes beyond traditional screen-time applications. By leveraging multi-modal AI (Google Gemini / OpenAI), offline-first desktop clients, and an Android companion app, Mimo actively monitors your behavior, categorizes application usage, and forcibly terminates distracting processes during scheduled focus blocks.

## Features

* **Strict Application Blocking:** Mimo actively polls the OS window manager. If time limits on distracting applications are exceeded during a scheduled study session, Mimo forces process termination (`taskkill`).
* **Multi-LLM Behavioral Analysis:** Native support for Google Gemini 2.5 Flash and OpenAI GPT-4o. The AI engine analyzes daily telemetry to identify productivity patterns, peak focus hours, and avoidance behaviors.
* **Offline-Resilient Desktop Client:** The standalone Windows executable caches screen telemetry locally in the event of a network disruption and synchronizes automatically with the central cloud database upon reconnection.
* **Distributed Cloud Architecture:** A decoupled architecture allows the FastAPI backend and PostgreSQL database to be hosted remotely via Docker, while lightweight clients stream data from end-user devices.
* **Android Companion App:** A native Kotlin Jetpack Compose application that monitors mobile application usage and mirrors the central web dashboard.
* **Physical Presence Verification (Optional):** Integration with ESP32-CAM via computer vision to verify physical desk presence.

## Architecture

Mimo is built using a decoupled client-server architecture:

1. **Central Server (`/api`)**: A FastAPI REST and WebSocket server connected to a PostgreSQL database. It handles user authentication, data aggregation, LLM inference scheduling, and serves the frontend dashboard.
2. **Desktop Client (`/desktop`)**: A PyInstaller-compiled background daemon that monitors active window titles and processes on Windows.
3. **Android Client (`/android`)**: A native Kotlin application interacting with the REST APIs to provide mobile telemetry and system notifications.

## Installation

### 1. Cloud Server Deployment (Docker)

The Mimo central server is designed to be deployed instantly using Docker Compose.

```bash
git clone https://github.com/SAM18-Bot/Mimo.git
cd Mimo

# Configure environment variables
echo "GEMINI_API_KEY=your_key_here" > .env
echo "NO_HARDWARE=1" >> .env
echo "NO_TRACKER=1" >> .env

# Build and start the backend and PostgreSQL database
docker-compose up --build -d
```
The server will now be accessible at `http://localhost:8000`.

### 2. Desktop Client (Windows)

To deploy the tracker to an end-user device, compile the standalone executable:

```bash
# Set the address of your deployed cloud server
set MIMO_CLOUD_URL=https://your-server-url.com

# Build the executable
python desktop/build.py
```
The resulting `dist/MimoDesktopTracker.exe` runs silently in the background (`--noconsole`) and automatically synchronizes with the configured `MIMO_CLOUD_URL`.

### 3. Android Application

To build the mobile companion app, use the included Gradle wrapper:

```bash
cd android
./gradlew assembleDebug
```
The resulting `.apk` will be located in `android/app/build/outputs/apk/debug/`.

## Development

To run the server locally for development purposes without Docker:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Contributing

Contributions are welcome. Please ensure that all pull requests pass existing test suites and adhere to PEP 8 standards for Python codebase modifications. For major architectural changes, please open an issue first to discuss the proposed modifications.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
