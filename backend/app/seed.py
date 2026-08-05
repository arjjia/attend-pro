import asyncio
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.database import SessionLocal
from app.models import Schedule, User
from app.security import hash_password


TYUMEN = ZoneInfo("Asia/Yekaterinburg")
GROUP = "РСОДПО-П-МОиАИС-23.01"
STUDENTS = [
    "Иванов Иван",
    "Петров Пётр",
    "Смирнова Анна",
    "Кузнецов Алексей",
    "Попова Мария",
    "Соколов Дмитрий",
    "Лебедева Екатерина",
    "Козлов Михаил",
    "Новикова Софья",
    "Морозов Артём",
    "Волкова Полина",
    "Соловьёв Максим",
    "Васильева Алина",
    "Зайцев Никита",
    "Павлова Дарья",
    "Семёнов Кирилл",
    "Голубева Виктория",
    "Виноградов Андрей",
    "Богданова Елизавета",
    "Воробьёв Роман",
    "Фёдорова Ксения",
    "Михайлов Сергей",
    "Беляева Валерия",
    "Тарасов Егор",
]


async def upsert_user(
    db: AsyncSession,
    email: str,
    full_name: str,
    role: str,
    group: str | None,
    password_hash: str,
) -> User:
    user = await db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, password_hash="", role=role, full_name=full_name, group=group)
        db.add(user)
    user.password_hash = password_hash
    user.role = role
    user.full_name = full_name
    user.group = group
    return user


async def seed() -> None:
    settings = get_settings()
    seed_day = date.fromisoformat(settings.seed_date) if settings.seed_date else datetime.now(TYUMEN).date()
    async with SessionLocal() as db:
        password_hash = hash_password("123456")
        student1 = await upsert_user(
            db, "student1@test.ru", "Иванов Иван", "student", GROUP, password_hash
        )
        student2 = await upsert_user(
            db, "student2@test.ru", "Петров Пётр", "student", GROUP, password_hash
        )
        lecturer = await upsert_user(
            db,
            "lecturer@test.ru",
            "Мельникова Антонина Владимировна",
            "lecturer",
            None,
            password_hash,
        )
        vorobieva = await upsert_user(
            db,
            "vorobieva@test.ru",
            "Воробьева Марина Сергеевна",
            "lecturer",
            None,
            password_hash,
        )
        del student1, student2
        await db.flush()
        schedule_specs = [
            {
                "module": "РСОДПО",
                "short_name": "Разработка интерфейса пользователя.",
                "full_name": "Разработка интерфейса пользователя. Практическое занятие",
                "type": "Практическое занятие",
                "form": "Проектный семинар",
                "audience": "Главный корпус / 209",
                "capacity": 30,
                "equipment": "Проектор",
                "start_time": datetime.combine(seed_day, time(15, 55), TYUMEN),
                "end_time": datetime.combine(seed_day, time(17, 25), TYUMEN),
                "duration": "1 п.",
                "lecturers": [lecturer, vorobieva],
            },
            {
                "module": "РСОДПО",
                "short_name": "Аттестация",
                "full_name": "Аттестация по программе МОиАИС",
                "type": "Аттестация",
                "form": "Аттестация",
                "audience": "Главный корпус / 209",
                "capacity": 30,
                "equipment": "Проектор",
                "start_time": datetime.combine(seed_day, time(17, 40), TYUMEN),
                "end_time": datetime.combine(seed_day, time(19, 10), TYUMEN),
                "duration": "1 п.",
                "lecturers": [lecturer],
            },
        ]
        for spec in schedule_specs:
            schedule = await db.scalar(
                select(Schedule)
                .options(selectinload(Schedule.lecturers))
                .where(
                    Schedule.module == spec["module"],
                    Schedule.short_name == spec["short_name"],
                    Schedule.group == GROUP,
                )
            )
            if schedule is None:
                schedule = Schedule(
                    module=spec["module"],
                    short_name=spec["short_name"],
                    full_name=spec["full_name"],
                    type=spec["type"],
                    form=spec["form"],
                    group=GROUP,
                    audience=spec["audience"],
                    capacity=spec["capacity"],
                    equipment=spec["equipment"],
                    start_time=spec["start_time"],
                    end_time=spec["end_time"],
                    duration=spec["duration"],
                    fact_passed=False,
                    students=STUDENTS,
                    allowed_late_minutes=15,
                )
                db.add(schedule)
            schedule.module = spec["module"]
            schedule.short_name = spec["short_name"]
            schedule.full_name = spec["full_name"]
            schedule.type = spec["type"]
            schedule.form = spec["form"]
            schedule.audience = spec["audience"]
            schedule.capacity = spec["capacity"]
            schedule.equipment = spec["equipment"]
            schedule.start_time = spec["start_time"]
            schedule.end_time = spec["end_time"]
            schedule.duration = spec["duration"]
            schedule.fact_passed = False
            schedule.students = STUDENTS
            schedule.lecturers = spec["lecturers"]
        await db.commit()
    print(f"Seeded AttendPro for {seed_day}: student1/student2/lecturer/vorobieva, password 123456")


if __name__ == "__main__":
    asyncio.run(seed())
