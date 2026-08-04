from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import Select, and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Schedule, User
from app.schemas import LecturerPublic, ScheduleCard


TYUMEN = ZoneInfo("Asia/Yekaterinburg")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def is_active(schedule: Schedule, now: datetime | None = None) -> bool:
    current = as_utc(now or utc_now())
    return (
        not schedule.fact_passed
        and as_utc(schedule.start_time) <= current <= as_utc(schedule.end_time)
    )


class ScheduleService:
    """Boundary for replacing local schedules with Modeus synchronization later."""

    async def for_user(
        self, db: AsyncSession, user: User, requested_date: date | None = None
    ) -> list[Schedule]:
        day = requested_date or utc_now().astimezone(TYUMEN).date()
        day_start = datetime.combine(day, time.min, TYUMEN).astimezone(timezone.utc)
        day_end = datetime.combine(day, time.max, TYUMEN).astimezone(timezone.utc)
        query: Select[tuple[Schedule]] = (
            select(Schedule)
            .options(selectinload(Schedule.lecturers))
            .where(and_(Schedule.start_time <= day_end, Schedule.end_time >= day_start))
            .order_by(Schedule.start_time)
        )
        if user.role == "student":
            if not user.group:
                return []
            query = query.where(Schedule.group == user.group)
        elif user.role == "lecturer":
            query = query.where(Schedule.lecturers.any(User.id == user.id))
        else:
            return []
        return list((await db.scalars(query)).all())

    async def get_with_lecturers(self, db: AsyncSession, schedule_id: int) -> Schedule | None:
        return await db.scalar(
            select(Schedule)
            .options(selectinload(Schedule.lecturers))
            .where(Schedule.id == schedule_id)
        )

    @staticmethod
    def to_card(schedule: Schedule) -> ScheduleCard:
        attendance_active = (
            schedule.attendance_started_at is not None
            and schedule.attendance_finished_at is None
        )
        return ScheduleCard(
            id=schedule.id,
            module=schedule.module,
            short_name=schedule.short_name,
            full_name=schedule.full_name,
            type=schedule.type,
            form=schedule.form,
            group=schedule.group,
            audience=schedule.audience,
            capacity=schedule.capacity,
            equipment=schedule.equipment,
            start_time=schedule.start_time,
            end_time=schedule.end_time,
            duration=schedule.duration,
            fact_passed=schedule.fact_passed,
            students=schedule.students,
            lecturers=[LecturerPublic.model_validate(item) for item in schedule.lecturers],
            active=is_active(schedule),
            attendance_active=attendance_active,
            allowed_late_minutes=schedule.allowed_late_minutes,
            attendance_started_at=schedule.attendance_started_at,
            attendance_finished_at=schedule.attendance_finished_at,
            exit_enabled=schedule.exit_enabled,
        )


schedule_service = ScheduleService()
