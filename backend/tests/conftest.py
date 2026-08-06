import os
import tempfile
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient


TEST_DB = Path(tempfile.gettempdir()) / f"attend-pro-signed-tests-{os.getpid()}.db"
TEST_KEY = Path(tempfile.gettempdir()) / f"attend-pro-portal-tests-{os.getpid()}.pem"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB}"
os.environ["SESSION_SECRET"] = "test-session-secret-at-least-thirty-two-bytes"
os.environ["PORTAL_PRIVATE_KEY_PATH"] = str(TEST_KEY)
os.environ["ENABLE_TEST_API"] = "true"

from app.database import Base, SessionLocal, engine, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed_database  # noqa: E402


@pytest_asyncio.fixture(autouse=True)
async def database():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    async with SessionLocal() as db:
        await seed_database(db)
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
