import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


TEST_DB = Path(tempfile.gettempdir()) / f"attend-pro-tests-{os.getpid()}.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB}"
os.environ["JWT_SECRET"] = "test-secret-at-least-thirty-two-bytes-long"

from app.database import Base, SessionLocal, engine, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Schedule, User  # noqa: E402
from app.security import hash_password  # noqa: E402


@pytest_asyncio.fixture(autouse=True)
async def database():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    await app.state.code_store.clear()

    now = datetime.now(timezone.utc)
    async with SessionLocal() as db:
        student = User(
            id=1,
            email="student1@test.ru",
            password_hash=hash_password("123456"),
            role="student",
            full_name="Иванов Иван",
            group="РСОДПО-П-МОиАИС-23.01",
        )
        other_student = User(
            id=2,
            email="student2@test.ru",
            password_hash=hash_password("123456"),
            role="student",
            full_name="Петров Пётр",
            group="РСОДПО-П-МОиАИС-23.01",
        )
        lecturer = User(
            id=3,
            email="lecturer@test.ru",
            password_hash=hash_password("123456"),
            role="lecturer",
            full_name="Мельникова Антонина Владимировна",
        )
        other_lecturer = User(
            id=4,
            email="vorobieva@test.ru",
            password_hash=hash_password("123456"),
            role="lecturer",
            full_name="Воробьева Марина Сергеевна",
        )
        outsider = User(
            id=5,
            email="outsider@test.ru",
            password_hash=hash_password("123456"),
            role="student",
            full_name="Сидоров Семён",
            group="ДРУГАЯ-ГРУППА",
        )
        active = Schedule(
            id=1,
            module="РСОДПО",
            short_name="МОиАИС",
            full_name="Математическое обеспечение и администрирование информационных систем",
            type="Практическое занятие",
            form="Проектный семинар",
            group="РСОДПО-П-МОиАИС-23.01",
            audience="Главный корпус / 209",
            capacity=30,
            equipment="Проектор",
            start_time=now - timedelta(minutes=5),
            end_time=now + timedelta(hours=1),
            duration="1 п.",
            fact_passed=False,
            students=[student.full_name, other_student.full_name],
            lecturers=[lecturer],
        )
        other_group = Schedule(
            id=2,
            module="РСОДПО",
            short_name="Чужая группа",
            full_name="Занятие другой группы",
            type="Лекция",
            form="Очно",
            group="ДРУГАЯ-ГРУППА",
            audience="Главный корпус / 101",
            capacity=20,
            equipment="Доска",
            start_time=now - timedelta(minutes=5),
            end_time=now + timedelta(hours=1),
            duration="1 п.",
            fact_passed=False,
            students=[outsider.full_name],
            lecturers=[other_lecturer],
        )
        future = Schedule(
            id=3,
            module="РСОДПО",
            short_name="Аттестация",
            full_name="Аттестация по программе МОиАИС",
            type="Аттестация",
            form="Аттестация",
            group="РСОДПО-П-МОиАИС-23.01",
            audience="Главный корпус / 209",
            capacity=30,
            equipment="Проектор",
            start_time=now + timedelta(hours=2),
            end_time=now + timedelta(hours=3),
            duration="1 п.",
            fact_passed=False,
            students=[student.full_name, other_student.full_name],
            lecturers=[lecturer],
        )
        db.add_all(
            [student, other_student, lecturer, other_lecturer, outsider, active, other_group, future]
        )
        await db.commit()
    yield
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)


async def override_db():
    async with SessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_db


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as test_client:
        yield test_client


async def login(client: AsyncClient, email: str) -> str:
    response = await client.post("/auth/login", json={"email": email, "password": "123456"})
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def auth_headers():
    async def make(client: AsyncClient, email: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {await login(client, email)}"}

    return make
