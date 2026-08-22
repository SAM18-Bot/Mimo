import asyncio
from fastapi.testclient import TestClient
from main import app
from modules.auth.security import create_access_token

token = create_access_token(user_id=999, role="student")

try:
    with TestClient(app) as client:
        with client.websocket_connect(f"/ws?token={token}") as websocket:
            print("Connected!")
            data = websocket.receive_text()
            print("Received:", data)
except Exception as e:
    print("Error:", e)
