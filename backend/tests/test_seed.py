from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload

from app.database import SessionLocal
from app.models import Attendance, Schedule, ScheduleLecturer, User
from app.seed import STUDENTS, seed
from app.security import verify_password


async def test_seed_is_idempotent_and_creates_complete_demo_data():
    async with SessionLocal() as db:
        await db.execute(delete(Attendance))
        await db.execute(delete(ScheduleLecturer))
        await db.execute(delete(Schedule))
        await db.execute(delete(User))
        await db.commit()

    await seed()
    await seed()

    async with SessionLocal() as db:
        users = (await db.scalars(select(User).order_by(User.email))).all()
        schedules = (
            await db.scalars(
                select(Schedule)
                .options(selectinload(Schedule.lecturers))
                .order_by(Schedule.start_time)
            )
        ).all()
        association_count = await db.scalar(select(func.count()).select_from(ScheduleLecturer))

    assert {user.email for user in users} == {
        "student1@test.ru",
        "student2@test.ru",
        "lecturer@test.ru",
        "vorobieva@test.ru",
    }
    assert all(verify_password("123456", user.password_hash) for user in users)
    assert len(schedules) == 2
    assert schedules[0].students == STUDENTS
    assert len(schedules[0].students) == 24
    names_by_email = {user.email: user.full_name for user in users}
    assert names_by_email["student1@test.ru"] == "Иванов Иван"
    assert names_by_email["student2@test.ru"] == "Петров Пётр"
    assert names_by_email["lecturer@test.ru"] == "Мельникова Антонина Владимировна"
    assert names_by_email["vorobieva@test.ru"] == "Воробьева Марина Сергеевна"
    assert {lecturer.email for lecturer in schedules[0].lecturers} == {
        "lecturer@test.ru",
        "vorobieva@test.ru",
    }
    first = schedules[0]
    assert first.module == "РСОДПО"
    assert first.short_name == "Разработка интерфейса пользователя."
    assert first.full_name == "Разработка интерфейса пользователя. Практическое занятие"
    assert first.type == "Практическое занятие"
    assert first.form == "Проектный семинар"
    assert first.group == "РСОДПО-П-МОиАИС-23.01"
    assert first.audience == "Главный корпус / 209"
    assert first.capacity == 30
    assert first.equipment == "Проектор"
    assert first.start_time.hour == 15 and first.start_time.minute == 55
    assert first.end_time.hour == 17 and first.end_time.minute == 25
    assert first.duration == "1 п."
    assert first.fact_passed is False
    assert schedules[1].type == "Аттестация"
    assert schedules[1].start_time != first.start_time
    assert {item.email for item in schedules[1].lecturers} == {"lecturer@test.ru"}
    assert association_count == 3
