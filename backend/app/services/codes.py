import asyncio
import base64
import io
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import qrcode


ROTATION_SECONDS = 15


@dataclass
class AttendanceCode:
    code: str
    generated_at: datetime
    expires_at: datetime


class AttendanceCodeStore:
    def __init__(self) -> None:
        self._entries: dict[int, AttendanceCode] = {}
        self._lock = asyncio.Lock()

    async def start(self, schedule_id: int) -> AttendanceCode:
        async with self._lock:
            entry = self._new_code()
            self._entries[schedule_id] = entry
            return entry

    async def current(self, schedule_id: int, rotate: bool = True) -> AttendanceCode | None:
        async with self._lock:
            entry = self._entries.get(schedule_id)
            if entry is None:
                return None
            if entry.expires_at <= datetime.now(timezone.utc):
                if not rotate:
                    return None
                entry = self._new_code()
                self._entries[schedule_id] = entry
            return entry

    async def stop(self, schedule_id: int) -> None:
        async with self._lock:
            self._entries.pop(schedule_id, None)

    async def clear(self) -> None:
        async with self._lock:
            self._entries.clear()

    @staticmethod
    def _new_code() -> AttendanceCode:
        generated_at = datetime.now(timezone.utc)
        return AttendanceCode(
            code=f"{secrets.randbelow(1_000_000):06d}",
            generated_at=generated_at,
            expires_at=generated_at + timedelta(seconds=ROTATION_SECONDS),
        )


def qr_data_uri(schedule_id: int, code: str) -> str:
    image = qrcode.make(f"attendpro://mark?schedule_id={schedule_id}&code={code}")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{encoded}"
