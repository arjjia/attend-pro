import pytest


@pytest.mark.asyncio
async def test_login_returns_bearer_token_and_user(client):
    response = await client.post(
        "/auth/login", json={"email": "student1@test.ru", "password": "123456"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["role"] == "student"
    assert body["user"]["full_name"] == "Иванов Иван"
    assert body["user"]["group"] == "РСОДПО-П-МОиАИС-23.01"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"email": "student1@test.ru", "password": "wrong"},
        {"email": "missing@test.ru", "password": "123456"},
    ],
)
async def test_login_rejects_invalid_credentials(client, payload):
    response = await client.post("/auth/login", json=payload)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_requires_valid_bearer(client):
    missing = await client.get("/schedule/current")
    invalid = await client.get(
        "/schedule/current", headers={"Authorization": "Bearer invalid"}
    )

    assert missing.status_code == 401
    assert invalid.status_code == 401
