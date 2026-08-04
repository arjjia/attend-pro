from datetime import date

from fastapi import APIRouter, Query

from app.dependencies import CurrentUser, DbSession
from app.schemas import ScheduleCard
from app.services.schedule import schedule_service


router = APIRouter(prefix="/schedule", tags=["schedule"])


@router.get("/current", response_model=list[ScheduleCard])
async def current_schedule(
    db: DbSession,
    user: CurrentUser,
    requested_date: date | None = Query(default=None, alias="date"),
) -> list[ScheduleCard]:
    schedules = await schedule_service.for_user(db, user, requested_date)
    return [schedule_service.to_card(schedule) for schedule in schedules]
