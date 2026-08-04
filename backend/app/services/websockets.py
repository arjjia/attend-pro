import asyncio
from collections import defaultdict

from fastapi import WebSocket


class AttendanceHub:
    def __init__(self) -> None:
        self._connections: dict[int, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, schedule_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[schedule_id].add(websocket)

    async def disconnect(self, schedule_id: int, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections[schedule_id].discard(websocket)
            if not self._connections[schedule_id]:
                self._connections.pop(schedule_id, None)

    async def broadcast(self, schedule_id: int, payload: dict[str, object]) -> None:
        async with self._lock:
            connections = list(self._connections.get(schedule_id, ()))
        stale: list[WebSocket] = []
        for websocket in connections:
            try:
                await websocket.send_json(payload)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            await self.disconnect(schedule_id, websocket)
