"""
WebSocket connection manager.

The event bus is a simple synchronous queue. Background threads (screen tracker,
CV pipeline, roast engine) push dicts onto it. The broadcaster coroutine
reads from it and sends to every connected dashboard client.

Usage from background threads (sync):
    from api.websocket import event_bus
    event_bus.put_nowait({"type": "roast", "message": "..."})

Usage from async routes:
    await manager.broadcast({"type": "ping"})
"""

import asyncio
import json
import logging
import queue
from collections import defaultdict
from typing import Dict, Optional, Set, Union

from fastapi import WebSocket, WebSocketDisconnect

log = logging.getLogger(__name__)

# Thread-safe queue — background threads push here, asyncio loop drains it
event_bus: queue.Queue = queue.Queue()


class ConnectionManager:
    def __init__(self):
        self._active: Set[WebSocket] = set()
        self._user_sockets: Dict[int, Set[WebSocket]] = defaultdict(set)
        self._socket_users: Dict[WebSocket, int] = {}

    async def connect(self, ws: WebSocket, user_id: int = 1):
        await ws.accept()
        self._active.add(ws)
        self._user_sockets[user_id].add(ws)
        self._socket_users[ws] = user_id
        log.info(f"Dashboard connected for user {user_id}. Total clients: {len(self._active)}")

    def disconnect(self, ws: WebSocket, user_id: Optional[int] = None):
        if user_id is None:
            user_id = self._socket_users.get(ws)

        self._active.discard(ws)
        if ws in self._socket_users:
            del self._socket_users[ws]

        if user_id is not None and user_id in self._user_sockets:
            self._user_sockets[user_id].discard(ws)
            if not self._user_sockets[user_id]:
                del self._user_sockets[user_id]

        log.info(f"Dashboard disconnected. Remaining: {len(self._active)}")

    async def unicast(self, user_id: int, message: Union[dict, str]):
        sockets = self._user_sockets.get(user_id)
        if not sockets:
            return
        payload = json.dumps(message) if isinstance(message, dict) else message
        dead = set()
        for ws in list(sockets):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.disconnect(ws, user_id)

    async def broadcast(self, message: Union[dict, str], user_id: Optional[int] = None):
        target_user = user_id
        if target_user is None and isinstance(message, dict):
            target_user = message.get("user_id")

        if target_user is not None:
            await self.unicast(target_user, message)
            return

        if not self._active:
            return
        payload = json.dumps(message) if isinstance(message, dict) else message
        dead = set()
        for ws in list(self._active):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.disconnect(ws)

    @property
    def client_count(self) -> int:
        return len(self._active)
    @property
    def connected_user_ids(self) -> Set[int]:
        return set(self._user_sockets.keys())


manager = ConnectionManager()


# ── drain loop ──────────────────────────────────────────────────────────
# Run this as a background asyncio task in main.py startup.

async def drain_event_bus():
    """Reads from the sync queue and broadcasts to WebSocket clients."""
    loop = asyncio.get_event_loop()
    while True:
        try:
            # Non-blocking check so we don't block the event loop
            data = event_bus.get_nowait()
            user_id = data.get("user_id") if isinstance(data, dict) else None
            await manager.broadcast(data, user_id=user_id)
        except queue.Empty:
            await asyncio.sleep(0.05)   # 50 ms polling — snappy enough
        except Exception as e:
            log.error(f"Drain loop error: {e}")
            await asyncio.sleep(0.2)


# ── convenience helper for sync threads ─────────────────────────────────
def push_event(data: dict):
    """Called from any background thread. Thread-safe."""
    event_bus.put_nowait(data)
