from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.dependencies import DbSession, StudentUser
from app.models import Attendance, Schedule
from app.schemas import HistoryItem, MarkRequest, MarkResponse
from app.services.attendance import attendance_for_schedule
from app.services.codes import AttendanceCodeStore
from app.services.schedule import as_utc, is_active, schedule_service
from app.services.websockets import AttendanceHub


router = APIRouter(prefix="/student", tags=["student"])


@router.post("/mark", response_model=MarkResponse, status_code=201)
async def mark_attendance(
    body: MarkRequest,
    request: Request,
    db: DbSession,
    student: StudentUser,
) -> MarkResponse:
    schedule = await schedule_service.get_with_lecturers(db, body.schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if student.group is None or schedule.group != student.group:
        raise HTTPException(status_code=403, detail="Student group does not match this class")
    if not is_active(schedule):
        raise HTTPException(status_code=409, detail="Class is not active")
    if schedule.attendance_started_at is None or schedule.attendance_finished_at is not None:
        raise HTTPException(status_code=409, detail="Attendance session is not running")

    store: AttendanceCodeStore = request.app.state.code_store
    entry = await store.current(schedule.id)
    if entry is None or entry.code != body.code:
        raise HTTPException(status_code=400, detail="Invalid or expired attendance code")

    duplicate = await db.scalar(
        select(Attendance.id).where(
            Attendance.user_id == student.id,
            Attendance.schedule_id == schedule.id,
            Attendance.type == body.type,
        )
    )
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="Attendance already marked")

    now = datetime.now(timezone.utc)
    late_minutes = max(0, int((now - as_utc(schedule.start_time)).total_seconds() // 60))
    is_credited = late_minutes <= schedule.allowed_late_minutes
    attendance = Attendance(
        user_id=student.id,
        schedule_id=schedule.id,
        timestamp=now,
        type=body.type,
        late_minutes=late_minutes,
        is_credited=is_credited,
    )
    db.add(attendance)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Attendance already marked") from None
    await db.refresh(attendance)

    items = await attendance_for_schedule(db, schedule.id)
    hub: AttendanceHub = request.app.state.attendance_hub
    await hub.broadcast(
        schedule.id,
        {
            "type": "attendance_updated",
            "schedule_id": schedule.id,
            "attendance": [item.model_dump(mode="json") for item in items],
        },
    )
    message = (
        "Посещение успешно отмечено"
        if is_credited
        else (
            "Посещение отмечено, но не засчитано: "
            f"опоздание превышает {schedule.allowed_late_minutes} мин."
        )
    )
    return MarkResponse(
        id=attendance.id,
        schedule_id=schedule.id,
        timestamp=attendance.timestamp,
        type=attendance.type,
        late_minutes=attendance.late_minutes,
        credited=attendance.is_credited,
        schedule_name=schedule.full_name,
        message=message,
    )


@router.get("/history", response_model=list[HistoryItem])
async def attendance_history(db: DbSession, student: StudentUser) -> list[HistoryItem]:
    records = (
        await db.scalars(
            select(Attendance)
            .options(joinedload(Attendance.schedule))
            .where(Attendance.user_id == student.id)
            .order_by(Attendance.timestamp.desc())
        )
    ).all()
    return [
        HistoryItem(
            id=record.id,
            schedule_id=record.schedule_id,
            schedule_name=record.schedule.full_name,
            start_time=record.schedule.start_time,
            timestamp=record.timestamp,
            audience=record.schedule.audience,
            type=record.type,
            late_minutes=record.late_minutes,
            credited=record.is_credited,
        )
        for record in records
    ]
