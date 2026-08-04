from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import SessionLocal
from app.models import Schedule, User
from app.security import decode_access_token
from app.services.websockets import AttendanceHub


router = APIRouter(tags=["websocket"])


@router.websocket("/ws/attendance/{schedule_id}")
async def attendance_websocket(websocket: WebSocket, schedule_id: int) -> None:
    token = websocket.query_params.get("token")
    try:
        if not token:
            raise ValueError
        user_id = decode_access_token(token)
        async with SessionLocal() as db:
            user = await db.get(User, user_id)
            schedule = await db.scalar(
                select(Schedule)
                .options(selectinload(Schedule.lecturers))
                .where(Schedule.id == schedule_id)
            )
        if (
            user is None
            or user.role != "lecturer"
            or schedule is None
            or user.id not in {lecturer.id for lecturer in schedule.lecturers}
        ):
            raise ValueError
    except ValueError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    hub: AttendanceHub = websocket.app.state.attendance_hub
    await hub.connect(schedule_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await hub.disconnect(schedule_id, websocket)
