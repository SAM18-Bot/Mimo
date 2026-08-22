import asyncio
import websockets
from modules.auth.security import create_access_token

async def test():
    token = create_access_token(user_id=1, role="student")
    try:
        async with websockets.connect(f"ws://127.0.0.1:8000/ws?token={token}") as ws:
            print("Connected!")
            res = await ws.recv()
            print("Received:", res)
    except Exception as e:
        print("Failed to connect:", e)

asyncio.run(test())
