from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models import Attendance
from app.schemas import AttendanceItem


async def attendance_for_schedule(
    db: AsyncSession, schedule_id: int
) -> list[AttendanceItem]:
    records = (
        await db.scalars(
            select(Attendance)
            .options(joinedload(Attendance.user))
            .where(Attendance.schedule_id == schedule_id)
            .order_by(Attendance.timestamp)
        )
    ).all()
    return [
        AttendanceItem(
            id=record.id,
            user_id=record.user_id,
            student_name=record.user.full_name,
            timestamp=record.timestamp,
            type=record.type,
            late_minutes=record.late_minutes,
            credited=record.is_credited,
        )
        for record in records
    ]
