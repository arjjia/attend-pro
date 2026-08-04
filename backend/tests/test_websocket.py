import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app


def test_websocket_rejects_invalid_token():
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect) as error:
            with client.websocket_connect("/ws/attendance/1?token=invalid"):
                pass

    assert error.value.code == 1008


def test_mark_broadcasts_updated_attendance_list():
    with TestClient(app) as client:
        lecturer_token = client.post(
            "/auth/login",
            json={"email": "lecturer@test.ru", "password": "123456"},
        ).json()["access_token"]
        student_token = client.post(
            "/auth/login",
            json={"email": "student1@test.ru", "password": "123456"},
        ).json()["access_token"]
        lecturer_headers = {"Authorization": f"Bearer {lecturer_token}"}
        code = client.post(
            "/lecturer/start/1", json={}, headers=lecturer_headers
        ).json()["code"]

        with client.websocket_connect(
            f"/ws/attendance/1?token={lecturer_token}"
        ) as websocket:
            marked = client.post(
                "/student/mark",
                json={"schedule_id": 1, "code": code},
                headers={"Authorization": f"Bearer {student_token}"},
            )
            message = websocket.receive_json()

    assert marked.status_code == 201
    assert message["type"] == "attendance_updated"
    assert message["schedule_id"] == 1
    assert message["attendance"][0]["student_name"] == "Иванов Иван"
    assert message["attendance"][0]["credited"] is True
