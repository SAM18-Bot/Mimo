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
from typing import Set

from fastapi import WebSocket, WebSocketDisconnect

log = logging.getLogger(__name__)

# Thread-safe queue — background threads push here, asyncio loop drains it
event_bus: queue.Queue = queue.Queue()


class ConnectionManager:
    def __init__(self):
        self._active: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._active.add(ws)
        log.info(f"Dashboard connected. Total clients: {len(self._active)}")

    def disconnect(self, ws: WebSocket):
        self._active.discard(ws)
        log.info(f"Dashboard disconnected. Remaining: {len(self._active)}")

    async def broadcast(self, data: dict):
        if not self._active:
            return
        payload = json.dumps(data)
        dead    = set()
        for ws in list(self._active):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self._active.discard(ws)

    @property
    def client_count(self) -> int:
        return len(self._active)


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
            await manager.broadcast(data)
        except queue.Empty:
            await asyncio.sleep(0.05)   # 50 ms polling — snappy enough
        except Exception as e:
            log.error(f"Drain loop error: {e}")
            await asyncio.sleep(0.2)


# ── convenience helper for sync threads ─────────────────────────────────
def push_event(data: dict):
    """Called from any background thread. Thread-safe."""
    event_bus.put_nowait(data)
