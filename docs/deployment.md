# Deploy the Mimo server

The server hosts the API, WebSocket connection, student dashboard and parent portal. Windows and Android can both connect to the same HTTPS origin. Use the repository root as the Docker build context.

## Docker Compose with PostgreSQL

Docker Compose starts the server and a PostgreSQL 15 service. Its named database volume keeps local data across container restarts.

1. Copy `.env.example` to `.env`.
2. Set `JWT_SECRET_KEY` and `SECRET_KEY` in `.env`. Generate the two values separately for a new installation.
3. Start the services and check the health endpoint.

```bash
# Generate JWT_SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(48))"

# Generate a Fernet-compatible SECRET_KEY
python -c "import base64, secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"

docker compose up --build -d
docker compose ps
curl --fail http://127.0.0.1:8000/health
```

Keep both keys in private configuration across deployments. The JWT key signs sessions. The Fernet key protects personal Gemini keys stored in the database. The Compose database credentials in this repository are for local development.

The production image runs as user and group `10001`. It installs Python 3.11, SQLite and the PostgreSQL client from Wolfi's signed package repository. For a container that uses SQLite, the default database is `/app/mimo.db`. Give that user write access to the database and its journal directory on an existing bind mount.

## Render with a managed PostgreSQL database

Create a PostgreSQL database and a Render Docker web service connected to this repository. The root [Dockerfile](../Dockerfile) installs the server dependencies, copies the backend and dashboard, and starts Uvicorn on Render’s assigned `PORT`. Use the image’s default start command and configure `/health` as the service health check.

| Environment variable | Use |
| --- | --- |
| `DATABASE_URL` | The database connection string. Mimo accepts PostgreSQL URLs and requires TLS for Neon hosts. |
| `JWT_SECRET_KEY` | A persistent, randomly generated signing secret. Production startup checks this value. |
| `SECRET_KEY` | A persistent Fernet key for encrypting and reading personal Gemini credentials. |
| `GEMINI_API_KEY` | Optional server-wide Gemini access. Students may also configure a personal key. |
| `GOOGLE_CLIENT_ID` | Optional Google sign-in. |
| `NO_HARDWARE`, `NO_VOICE` | The hosted image defaults both to `1`. Camera and microphone integrations run on a suitably equipped local machine. |

Mimo applies [Alembic migrations](../server/db/migrations/) before accepting traffic. Back up an existing database before upgrading. Startup recognizes an older unversioned Mimo schema and stops on an unfamiliar schema so it can be reviewed.

After deployment, visit `/health` and sign in to the student dashboard at `/`. An authenticated request to `/reports/stats` exercises account access and the database. The interactive API reference is at `/docs`. Use the [client guide](clients.md) to point a client at the new origin.

If a deploy stops with `Set a strong JWT_SECRET_KEY for production`, open the service's **Environment** tab. Set a persistent signing key using the first command above and keep the existing Fernet key. For a new installation, generate the Fernet key with the second command. Select **Save, rebuild, and deploy**. In **Events**, check that the live deploy lists the intended Git commit. Its `/openapi.json` should include `GET /reports/accountability/questions` and `PUT /auth/me/gemini-key`.

## Optional desk camera

The [ESP32-CAM sketch](../firmware/cam_stream/cam_stream.ino) serves an MJPEG stream. On a local Mimo installation with the full Python dependencies, configure `ESP32_STREAM_URL` for the camera on your network and set `NO_HARDWARE=0`. The sketch contains the board selection, pin map and Wi-Fi configuration instructions.
