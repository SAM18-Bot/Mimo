"""Launch a packaged desktop app in local mode and verify its embedded backend."""

import base64
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time

import httpx


def check_bundle(executable: Path) -> None:
    executable = executable.resolve(strict=True)
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 8000)) == 0:
            raise RuntimeError("The desktop app requires a free local port 8000")
    with tempfile.TemporaryDirectory() as directory:
        database = (Path(directory) / "smoke.sqlite").as_posix()
        env = dict(os.environ, MIMO_CLOUD_URL="local", MIMO_ENV="production",
                   DATABASE_URL="sqlite:///" + database, NO_VOICE="1", NO_HARDWARE="1",
                   SECRET_KEY=base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
                   JWT_SECRET_KEY=secrets.token_urlsafe(48))
        process = subprocess.Popen([str(executable)], cwd=directory, env=env)
        try:
            with httpx.Client(base_url="http://127.0.0.1:8000", timeout=3, trust_env=False) as client:
                deadline = time.monotonic() + 120
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        raise RuntimeError(f"Desktop app exited with code {process.returncode}")
                    try:
                        if client.get("/health").json().get("status") == "ok":
                            break
                    except (httpx.HTTPError, ValueError):
                        pass
                    time.sleep(1)
                else:
                    raise RuntimeError("Packaged backend failed to become healthy")
                for path in ("/", "/schedule", "/settings", "/parents", "/static/vendor/chart-4.5.1.min.js"):
                    client.get(path).raise_for_status()
                signup = client.post("/auth/register", json={
                    "email": "desktop-smoke@example.org", "password": secrets.token_urlsafe(20)})
                signup.raise_for_status()
                session = {"Authorization": "Bearer " + signup.json()["access_token"]}
                client.get("/reports/stats", headers=session).raise_for_status()
                assert client.get("/auth/me", headers=session).json()["email"] == "desktop-smoke@example.org"
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
    print("Packaged desktop startup, pages, assets and authenticated API passed.")


if __name__ == "__main__":
    check_bundle(Path(sys.argv[1]))
