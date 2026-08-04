from datetime import datetime, timedelta, timezone

import pytest


@pytest.mark.asyncio
async def test_only_lecturer_can_start_attendance(client, auth_headers):
    headers = await auth_headers(client, "student1@test.ru")

    response = await client.post("/lecturer/start/1", json={}, headers=headers)

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_lecturer_must_be_assigned(client, auth_headers):
    headers = await auth_headers(client, "lecturer@test.ru")

    response = await client.post("/lecturer/start/2", json={}, headers=headers)

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_start_requires_active_class(client, auth_headers):
    headers = await auth_headers(client, "lecturer@test.ru")

    response = await client.post("/lecturer/start/3", json={}, headers=headers)

    assert response.status_code == 409
    assert response.json()["detail"] == "Class is not active"


@pytest.mark.asyncio
async def test_code_lifecycle_rotates_and_stops(client, auth_headers):
    headers = await auth_headers(client, "lecturer@test.ru")
    started = await client.post(
        "/lecturer/start/1",
        json={"allowed_late_minutes": 10, "exit_enabled": True},
        headers=headers,
    )

    assert started.status_code == 200
    first = started.json()
    assert first["code"].isdigit() and len(first["code"]) == 6
    assert first["qr_code"].startswith("data:image/png;base64,")
    assert 1 <= first["expires_in"] <= 15
    assert first["rotation_seconds"] == 15

    current = await client.get("/lecturer/code/1", headers=headers)
    assert current.status_code == 200
    assert current.json()["code"] == first["code"]

    from app.main import app

    entry = app.state.code_store._entries[1]
    entry.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    rotated = await client.get("/lecturer/code/1", headers=headers)
    assert rotated.status_code == 200
    assert rotated.json()["code"] != first["code"]

    stopped = await client.post("/lecturer/stop/1", headers=headers)
    assert stopped.status_code == 200
    unavailable = await client.get("/lecturer/code/1", headers=headers)
    assert unavailable.status_code == 409


@pytest.mark.asyncio
async def test_stop_requires_running_session(client, auth_headers):
    headers = await auth_headers(client, "lecturer@test.ru")

    response = await client.post("/lecturer/stop/1", headers=headers)

    assert response.status_code == 409


def test_openapi_contains_only_exact_lecturer_routes():
    from app.main import app

    paths = app.openapi()["paths"]
    assert {
        "/lecturer/start/{schedule_id}",
        "/lecturer/code/{schedule_id}",
        "/lecturer/stop/{schedule_id}",
        "/lecturer/attendance/{schedule_id}",
    } <= paths.keys()
    assert not any(path.startswith("/lecturer/schedule/") for path in paths)
