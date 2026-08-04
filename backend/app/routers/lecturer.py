import math
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from app.dependencies import DbSession, LecturerUser
from app.models import Schedule
from app.schemas import (
    AttendanceItem,
    CodeResponse,
    StartAttendanceRequest,
    StopResponse,
)
from app.services.attendance import attendance_for_schedule
from app.services.codes import AttendanceCodeStore, ROTATION_SECONDS, qr_data_uri
from app.services.schedule import is_active, schedule_service


router = APIRouter(prefix="/lecturer", tags=["lecturer"])


def ensure_assigned(schedule: Schedule | None, lecturer_id: int) -> Schedule:
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if lecturer_id not in {lecturer.id for lecturer in schedule.lecturers}:
        raise HTTPException(status_code=403, detail="Lecturer is not assigned to this class")
    return schedule


def code_response(schedule_id: int, code: str, expires_at: datetime) -> CodeResponse:
    expires_in = max(0, math.ceil((expires_at - datetime.now(timezone.utc)).total_seconds()))
    return CodeResponse(
        code=code,
        qr_code=qr_data_uri(schedule_id, code),
        expires_in=expires_in,
        schedule_id=schedule_id,
        expires_at=expires_at,
        rotation_seconds=ROTATION_SECONDS,
    )


@router.post("/start/{schedule_id}", response_model=CodeResponse)
async def start_attendance(
    schedule_id: int,
    body: StartAttendanceRequest,
    request: Request,
    db: DbSession,
    lecturer: LecturerUser,
) -> CodeResponse:
    schedule = ensure_assigned(
        await schedule_service.get_with_lecturers(db, schedule_id), lecturer.id
    )
    if not is_active(schedule):
        raise HTTPException(status_code=409, detail="Class is not active")
    now = datetime.now(timezone.utc)
    schedule.allowed_late_minutes = body.allowed_late_minutes
    schedule.exit_enabled = body.exit_enabled
    schedule.attendance_started_at = now
    schedule.attendance_finished_at = None
    await db.commit()
    store: AttendanceCodeStore = request.app.state.code_store
    entry = await store.start(schedule_id)
    return code_response(schedule_id, entry.code, entry.expires_at)


@router.get("/code/{schedule_id}", response_model=CodeResponse)
async def get_code(
    schedule_id: int,
    request: Request,
    db: DbSession,
    lecturer: LecturerUser,
) -> CodeResponse:
    schedule = ensure_assigned(
        await schedule_service.get_with_lecturers(db, schedule_id), lecturer.id
    )
    if schedule.attendance_started_at is None or schedule.attendance_finished_at is not None:
        raise HTTPException(status_code=409, detail="Attendance session is not running")
    store: AttendanceCodeStore = request.app.state.code_store
    entry = await store.current(schedule_id)
    if entry is None:
        raise HTTPException(status_code=409, detail="Attendance code is unavailable; start again")
    return code_response(schedule_id, entry.code, entry.expires_at)


@router.post("/stop/{schedule_id}", response_model=StopResponse)
async def stop_attendance(
    schedule_id: int,
    request: Request,
    db: DbSession,
    lecturer: LecturerUser,
) -> StopResponse:
    schedule = ensure_assigned(
        await schedule_service.get_with_lecturers(db, schedule_id), lecturer.id
    )
    if schedule.attendance_started_at is None or schedule.attendance_finished_at is not None:
        raise HTTPException(status_code=409, detail="Attendance session is not running")
    stopped_at = datetime.now(timezone.utc)
    schedule.attendance_finished_at = stopped_at
    await db.commit()
    store: AttendanceCodeStore = request.app.state.code_store
    await store.stop(schedule_id)
    return StopResponse(schedule_id=schedule_id, stopped_at=stopped_at)


@router.get("/attendance/{schedule_id}", response_model=list[AttendanceItem])
async def get_attendance(
    schedule_id: int,
    db: DbSession,
    lecturer: LecturerUser,
) -> list[AttendanceItem]:
    ensure_assigned(await schedule_service.get_with_lecturers(db, schedule_id), lecturer.id)
    return await attendance_for_schedule(db, schedule_id)
