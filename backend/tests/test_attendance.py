import pytest


async def start(client, auth_headers, allowed_late_minutes=15):
    lecturer = await auth_headers(client, "lecturer@test.ru")
    response = await client.post(
        "/lecturer/start/1",
        json={"allowed_late_minutes": allowed_late_minutes},
        headers=lecturer,
    )
    assert response.status_code == 200
    return response.json()["code"], lecturer


@pytest.mark.asyncio
async def test_student_marks_credited_attendance(client, auth_headers):
    code, _ = await start(client, auth_headers, allowed_late_minutes=15)
    student = await auth_headers(client, "student1@test.ru")

    response = await client.post(
        "/student/mark", json={"schedule_id": 1, "code": code}, headers=student
    )

    assert response.status_code == 201
    body = response.json()
    assert body["type"] == "entry"
    assert 4 <= body["late_minutes"] <= 6
    assert body["credited"] is True
    assert body["message"] == "Посещение успешно отмечено"
    assert body["schedule_name"] == (
        "Математическое обеспечение и администрирование информационных систем"
    )


@pytest.mark.asyncio
async def test_late_mark_is_saved_but_not_credited(client, auth_headers):
    code, lecturer = await start(client, auth_headers, allowed_late_minutes=1)
    student = await auth_headers(client, "student1@test.ru")

    response = await client.post(
        "/student/mark", json={"schedule_id": 1, "code": code}, headers=student
    )

    assert response.status_code == 201
    assert response.json()["credited"] is False
    assert response.json()["message"] == (
        "Посещение отмечено, но не засчитано: опоздание превышает 1 мин."
    )
    attendance = await client.get("/lecturer/attendance/1", headers=lecturer)
    assert attendance.status_code == 200
    assert attendance.json()[0]["credited"] is False


@pytest.mark.asyncio
async def test_duplicate_mark_returns_useful_conflict(client, auth_headers):
    code, _ = await start(client, auth_headers)
    student = await auth_headers(client, "student1@test.ru")
    payload = {"schedule_id": 1, "code": code}

    first = await client.post("/student/mark", json=payload, headers=student)
    duplicate = await client.post("/student/mark", json=payload, headers=student)

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "Attendance already marked"


@pytest.mark.asyncio
async def test_invalid_code_is_rejected_without_saving(client, auth_headers):
    _, lecturer = await start(client, auth_headers)
    student = await auth_headers(client, "student1@test.ru")

    response = await client.post(
        "/student/mark", json={"schedule_id": 1, "code": "000000"}, headers=student
    )

    assert response.status_code == 400
    attendance = await client.get("/lecturer/attendance/1", headers=lecturer)
    assert attendance.json() == []


@pytest.mark.asyncio
async def test_wrong_group_cannot_mark(client, auth_headers):
    code, _ = await start(client, auth_headers)
    other_student = await auth_headers(client, "outsider@test.ru")

    response = await client.post(
        "/student/mark", json={"schedule_id": 1, "code": code}, headers=other_student
    )

    assert response.status_code == 403
    assert "group" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_mark_requires_running_session(client, auth_headers):
    student = await auth_headers(client, "student1@test.ru")

    response = await client.post(
        "/student/mark", json={"schedule_id": 1, "code": "123456"}, headers=student
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Attendance session is not running"


@pytest.mark.asyncio
async def test_history_and_lecturer_attendance_contain_mark(client, auth_headers):
    code, lecturer = await start(client, auth_headers)
    student = await auth_headers(client, "student1@test.ru")
    await client.post(
        "/student/mark", json={"schedule_id": 1, "code": code}, headers=student
    )

    history = await client.get("/student/history", headers=student)
    attendance = await client.get("/lecturer/attendance/1", headers=lecturer)

    assert history.status_code == 200
    assert history.json()[0]["schedule_name"] == (
        "Математическое обеспечение и администрирование информационных систем"
    )
    assert history.json()[0]["audience"] == "Главный корпус / 209"
    assert history.json()[0]["credited"] is True
    assert history.json()[0]["schedule_id"] == 1
    assert attendance.status_code == 200
    assert attendance.json()[0]["student_name"] == "Иванов Иван"


@pytest.mark.asyncio
async def test_lecturer_cannot_use_student_routes(client, auth_headers):
    lecturer = await auth_headers(client, "lecturer@test.ru")

    history = await client.get("/student/history", headers=lecturer)
    mark = await client.post(
        "/student/mark",
        json={"schedule_id": 1, "code": "123456"},
        headers=lecturer,
    )

    assert history.status_code == 403
    assert mark.status_code == 403
