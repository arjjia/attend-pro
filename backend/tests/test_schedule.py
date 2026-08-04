from datetime import datetime
from zoneinfo import ZoneInfo

import pytest


@pytest.mark.asyncio
async def test_student_schedule_is_filtered_by_group(client, auth_headers):
    headers = await auth_headers(client, "student1@test.ru")

    response = await client.get("/schedule/current", headers=headers)

    assert response.status_code == 200
    cards = response.json()
    assert "МОиАИС" in {card["short_name"] for card in cards}
    assert "Чужая группа" not in {card["short_name"] for card in cards}
    assert all(card["group"] == "РСОДПО-П-МОиАИС-23.01" for card in cards)
    card = next(item for item in cards if item["short_name"] == "МОиАИС")
    assert card["active"] is True
    assert card["students"] == ["Иванов Иван", "Петров Пётр"]
    assert card["lecturers"][0]["full_name"] == "Мельникова Антонина Владимировна"
    assert {
        "module",
        "short_name",
        "full_name",
        "type",
        "form",
        "group",
        "audience",
        "capacity",
        "equipment",
        "start_time",
        "end_time",
        "duration",
        "fact_passed",
    } <= card.keys()


@pytest.mark.asyncio
async def test_lecturer_schedule_is_filtered_by_assignment(client, auth_headers):
    headers = await auth_headers(client, "lecturer@test.ru")

    response = await client.get("/schedule/current", headers=headers)

    assert response.status_code == 200
    names = {card["short_name"] for card in response.json()}
    assert "МОиАИС" in names
    assert "Чужая группа" not in names


@pytest.mark.asyncio
async def test_schedule_accepts_iso_date_filter(client, auth_headers):
    headers = await auth_headers(client, "student1@test.ru")
    response = await client.get(
        "/schedule/current",
        params={"date": datetime.now(ZoneInfo("Asia/Yekaterinburg")).date().isoformat()},
        headers=headers,
    )

    assert response.status_code == 200
    assert any(card["short_name"] == "МОиАИС" for card in response.json())


@pytest.mark.asyncio
async def test_invalid_schedule_date_is_rejected(client, auth_headers):
    headers = await auth_headers(client, "student1@test.ru")
    response = await client.get(
        "/schedule/current", params={"date": "tomorrow"}, headers=headers
    )

    assert response.status_code == 422
