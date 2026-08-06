import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import SessionLocal
from app.models import Lesson, LessonMember, User


TEACHER_ID = "00000000-0000-4000-8000-000000000001"
STUDENT_IDS = [
    "00000000-0000-4000-8000-000000000101",
    "00000000-0000-4000-8000-000000000102",
    "00000000-0000-4000-8000-000000000103",
]
CURRENT_LESSON_ID = "10000000-0000-4000-8000-000000000001"
NEXT_LESSON_ID = "10000000-0000-4000-8000-000000000002"
GROUP = "РСОДПО-П-МОиАИС-23.01"


async def seed_database(db: AsyncSession, now: datetime | None = None) -> None:
    now = now or datetime.now(timezone.utc)
    users = [
        User(
            id=TEACHER_ID,
            email="teacher@attend.test",
            role="teacher",
            full_name="Мельникова Антонина Владимировна",
            group_name=None,
            active=True,
        ),
        User(
            id=STUDENT_IDS[0],
            email="student1@attend.test",
            role="student",
            full_name="Иванов Иван",
            group_name=GROUP,
            active=True,
        ),
        User(
            id=STUDENT_IDS[1],
            email="student2@attend.test",
            role="student",
            full_name="Петрова Анна",
            group_name=GROUP,
            active=True,
        ),
        User(
            id=STUDENT_IDS[2],
            email="student3@attend.test",
            role="student",
            full_name="Смирнов Максим",
            group_name=GROUP,
            active=True,
        ),
    ]
    for candidate in users:
        stored = await db.get(User, candidate.id)
        if stored is None:
            db.add(candidate)
        else:
            stored.email = candidate.email
            stored.role = candidate.role
            stored.full_name = candidate.full_name
            stored.group_name = candidate.group_name
            stored.active = True
    await db.flush()

    specs = [
        Lesson(
            id=CURRENT_LESSON_ID,
            course_code="БКИТ-2026",
            title="Архитектура информационных систем",
            kind="Практическое занятие",
            group_name=GROUP,
            room="Главный корпус / 209",
            starts_at=now - timedelta(minutes=10),
            ends_at=now + timedelta(minutes=80),
            teacher_id=TEACHER_ID,
            test_managed=True,
        ),
        Lesson(
            id=NEXT_LESSON_ID,
            course_code="БКИТ-2026",
            title="Криптография прикладных протоколов",
            kind="Лекция",
            group_name=GROUP,
            room="Главный корпус / 305",
            starts_at=now + timedelta(days=1),
            ends_at=now + timedelta(days=1, minutes=90),
            teacher_id=TEACHER_ID,
            test_managed=True,
        ),
    ]
    for candidate in specs:
        stored = await db.get(Lesson, candidate.id)
        if stored is None:
            db.add(candidate)
        else:
            stored.course_code = candidate.course_code
            stored.title = candidate.title
            stored.kind = candidate.kind
            stored.group_name = candidate.group_name
            stored.room = candidate.room
            if candidate.id == CURRENT_LESSON_ID and stored.ends_at < now:
                stored.starts_at = candidate.starts_at
                stored.ends_at = candidate.ends_at
            stored.teacher_id = candidate.teacher_id
            stored.test_managed = True
    await db.flush()
    for lesson_id in (CURRENT_LESSON_ID, NEXT_LESSON_ID):
        for student_id in STUDENT_IDS:
            if await db.get(LessonMember, (lesson_id, student_id)) is None:
                db.add(LessonMember(lesson_id=lesson_id, student_id=student_id))
    await db.commit()


async def seed() -> None:
    async with SessionLocal() as db:
        await seed_database(db)
    print("Seeded mock SSO: teacher@attend.test and student1..3@attend.test")
    print("The first lesson is current; POST /api/v1/test/lessons/start-now restarts it.")


if __name__ == "__main__":
    asyncio.run(seed())
