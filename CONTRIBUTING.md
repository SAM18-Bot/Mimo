# Contributing to Mimo

The [repository guide](README.md#repository-guide) maps each client and the shared server to its source directory. Run the commands below from the repository root unless a step changes directories.

## Local development

Use Python 3.11. The server dependency list is enough for the web dashboard, SQLite or PostgreSQL, and account and planning features.

**macOS or Linux**

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements_server.txt
NO_HARDWARE=1 NO_VOICE=1 python -m uvicorn server.main:app --reload --host 127.0.0.1 --port 8000
```

**Windows PowerShell**

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements_server.txt
$env:NO_HARDWARE = "1"
$env:NO_VOICE = "1"
.\.venv\Scripts\python.exe -m uvicorn server.main:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/` to register a student account. The root ASGI entry point `main:app` and the `run_server.py` launcher also work. For persistent local configuration, copy [.env.example](.env.example) to `.env`. Production settings are covered in the [deployment guide](docs/deployment.md).

## Run the checks for your change

| Area | Check |
| --- | --- |
| Python server and desktop logic | Install the full development dependencies with `python -m pip install -r requirements.txt pytest`. Run `python -m pytest tests/ desktop/tests/`. CI uses Python 3.11. |
| Dashboard and parent portal | Install Playwright with `python -m pip install playwright` and `python -m playwright install chromium`. Start a disposable server and run `python scripts/check_dashboard.py http://127.0.0.1:8000`. The check creates test accounts and exercises four viewport widths. |
| Production container | Run `docker build -t mimo-server:local .` and then `bash scripts/check_server_image.sh mimo-server:local`. CI also tests PostgreSQL and publishes the Grype scan as `Mimo-server-security` on each [backend workflow run](https://github.com/SAM18-Bot/Mimo/actions/workflows/backend.yml). |
| Android app | In `android/`, run `./gradlew assembleDebug testDebugUnitTest lintDebug`. On Windows use `gradlew.bat`. |
| Native Android journeys | With a dedicated Android emulator running, use `bash scripts/check_android_device.sh` from the root. The script runs a disposable HTTPS backend and exercises the student and parent flows. |
| Windows bundle | Build on Windows and run `python scripts/check_desktop_bundle.py dist/Mimo/Mimo.exe`. See the [client guide](docs/clients.md). |

The Python requirements include optional computer-vision, audio and desktop libraries. CI runs a separate production-image check with the smaller server dependency set. For UI changes, `MIMO_CHROME_EXECUTABLE` can point the browser check at an installed Chromium executable.

## Database migrations and web assets

Alembic revisions live in [server/db/migrations/versions](server/db/migrations/versions/). Set `DATABASE_URL` to a disposable database while developing a migration. Run `python -m alembic upgrade head` and `python -m alembic current` to apply and inspect it. The checked-in [Alembic configuration](alembic.ini) also supports running from another directory with an explicit `-c` path.

Dashboard HTML and JavaScript live in [web/](web/). If you change a bundled library or a Tailwind utility used in the dashboard or parent portal, run `bash scripts/build_dashboard_assets.sh` with Node.js and npm available. Commit the corresponding vendored files and keep their license notices.

## Pull requests

Describe the user-visible change and the checks you ran. For a UI change, a screenshot at the affected viewport helps reviewers. Keep local databases, credentials, keystores and generated app bundles out of commits. The [GitHub Actions workflows](.github/workflows/) show the build and test commands used by the project.
