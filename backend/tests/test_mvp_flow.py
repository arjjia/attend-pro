from datetime import datetime, timedelta, timezone
from uuid import uuid4

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

from app.security import b64url_encode, canonical_digest, canonical_json, get_portal_signer, public_jwk


def browser_sign(key: ec.EllipticCurvePrivateKey, payload: dict) -> str:
    der = key.sign(canonical_json(payload), ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der)
    return b64url_encode(r.to_bytes(32, "big") + s.to_bytes(32, "big"))


async def login(client, email: str) -> dict:
    response = await client.post("/api/v1/auth/mock/login", json={"email": email})
    assert response.status_code == 200, response.text
    return response.json()


async def enroll(client, label: str) -> tuple[ec.EllipticCurvePrivateKey, dict]:
    key = ec.generate_private_key(ec.SECP256R1())
    response = await client.post(
        "/api/v1/devices/enroll",
        json={
            "device_id": str(uuid4()),
            "label": label,
            "public_key_jwk": public_jwk(key.public_key()),
        },
    )
    assert response.status_code == 200, response.text
    return key, response.json()


async def signed_proof(client) -> tuple[dict, dict, ec.EllipticCurvePrivateKey]:
    await login(client, "teacher@attend.test")
    teacher_key, teacher_credential = await enroll(client, "Teacher test browser")
    lesson = (await client.get("/api/v1/schedule/current")).json()
    permit_response = await client.post(
        f"/api/v1/lessons/{lesson['id']}/permit",
        json={"device_credential_id": teacher_credential["payload"]["credential_id"]},
    )
    assert permit_response.status_code == 200, permit_response.text
    permit_bundle = permit_response.json()
    now = datetime.now(timezone.utc)
    challenge_payload = {
        "version": "attendpro.teacher-challenge.v1",
        "challenge_id": str(uuid4()),
        "lesson_id": lesson["id"],
        "permit_id": permit_bundle["permit"]["payload"]["permit_id"],
        "teacher_device_id": teacher_credential["payload"]["device_id"],
        "kind": "ENTRY",
        "nonce": b64url_encode(os_random(32)),
        "issued_at": instant(now),
        "expires_at": instant(now + timedelta(seconds=90)),
    }
    challenge = {
        "payload": challenge_payload,
        "signature": browser_sign(teacher_key, challenge_payload),
        "key_id": teacher_credential["payload"]["device_id"],
        "algorithm": "ES256",
    }

    student = await login(client, "student1@attend.test")
    student_key, student_credential = await enroll(client, "Student test browser")
    claim_payload = {
        "version": "attendpro.student-claim.v1",
        "claim_id": str(uuid4()),
        "challenge_id": challenge_payload["challenge_id"],
        "challenge_digest": canonical_digest(challenge),
        "lesson_id": lesson["id"],
        "kind": "ENTRY",
        "student_user_id": student["id"],
        "student_device_id": student_credential["payload"]["device_id"],
        "captured_at": instant(now + timedelta(seconds=1)),
    }
    claim = {
        "payload": claim_payload,
        "signature": browser_sign(student_key, claim_payload),
        "key_id": student_credential["payload"]["device_id"],
        "algorithm": "ES256",
    }
    proof = {
        "teacher_credential": permit_bundle["teacher_credential"],
        "permit": permit_bundle["permit"],
        "challenge": challenge,
        "student_credential": student_credential,
        "claim": claim,
    }
    return proof, lesson, student_key


def os_random(length: int) -> bytes:
    import os

    return os.urandom(length)


def instant(value: datetime) -> str:
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


async def test_mock_sso_has_exact_mvp_accounts_and_http_only_cookie(client):
    response = await client.get("/api/v1/auth/mock/accounts")
    assert response.status_code == 200
    accounts = response.json()
    assert len(accounts) == 4
    assert {account["email"] for account in accounts} == {
        "teacher@attend.test",
        "student1@attend.test",
        "student2@attend.test",
        "student3@attend.test",
    }
    response = await client.post(
        "/api/v1/auth/mock/login", json={"email": "student1@attend.test"}
    )
    assert "HttpOnly" in response.headers["set-cookie"]
    assert (await client.get("/api/v1/auth/me")).json()["role"] == "student"


async def test_teacher_can_restart_the_demo_lesson_and_issue_signed_permit(client):
    await login(client, "teacher@attend.test")
    _, credential = await enroll(client, "Teacher")
    restart = await client.post("/api/v1/test/lessons/start-now", json={})
    assert restart.status_code == 200
    assert restart.json()["state"] == "current"
    permit = await client.post(
        f"/api/v1/lessons/{restart.json()['id']}/permit",
        json={"device_credential_id": credential["payload"]["credential_id"]},
    )
    assert permit.status_code == 200
    bundle = permit.json()
    signer = get_portal_signer()
    assert signer.verify(bundle["teacher_credential"]["payload"], bundle["teacher_credential"]["signature"])
    assert signer.verify(bundle["permit"]["payload"], bundle["permit"]["signature"])


async def test_complete_offline_proof_is_accepted_and_idempotent(client):
    proof, lesson, _ = await signed_proof(client)
    proof["replica_refs"] = ["giper://demo-land/demo-claim"]
    response = await client.post("/api/v1/claims/sync", json={"claims": [proof]})
    assert response.status_code == 200, response.text
    result = response.json()["results"][0]
    assert result["decision"]["payload"]["status"] == "ACCEPTED"
    assert result["decision"]["payload"]["reason_code"] == "PROOF_VALID"
    assert get_portal_signer().verify(
        result["decision"]["payload"], result["decision"]["signature"]
    )

    replay = await client.post("/api/v1/claims/sync", json={"claims": [proof]})
    assert replay.status_code == 200
    assert replay.json()["results"][0]["decision"] == result["decision"]
    history = await client.get("/api/v1/attendance/me")
    assert len(history.json()) == 1
    assert history.json()[0]["lesson_id"] == lesson["id"]
    assert history.json()[0]["giper_document_id"] == "giper://demo-land/demo-claim"


async def test_tampered_claim_is_cryptographically_rejected(client):
    proof, _, _ = await signed_proof(client)
    proof["claim"]["payload"]["kind"] = "EXIT"
    response = await client.post("/api/v1/claims/sync", json={"claims": [proof]})
    assert response.status_code == 200
    decision = response.json()["results"][0]["decision"]
    assert decision["payload"]["status"] == "REJECTED"
    assert decision["payload"]["reason_code"] == "INVALID_STUDENT_SIGNATURE"


async def test_malformed_claim_identifier_is_rejected_without_database_error(client):
    proof, _, student_key = await signed_proof(client)
    proof["claim"]["payload"]["claim_id"] = "not-a-uuid"
    proof["claim"]["signature"] = browser_sign(student_key, proof["claim"]["payload"])
    response = await client.post("/api/v1/claims/sync", json={"claims": [proof]})
    assert response.status_code == 200
    decision = response.json()["results"][0]["decision"]
    assert decision["payload"]["reason_code"] == "MALFORMED_PROOF"


async def test_student_cannot_start_lesson_or_request_teacher_permit(client):
    await login(client, "student2@attend.test")
    _, credential = await enroll(client, "Student")
    lesson = (await client.get("/api/v1/schedule/current")).json()
    assert (await client.post("/api/v1/test/lessons/start-now", json={})).status_code == 403
    response = await client.post(
        f"/api/v1/lessons/{lesson['id']}/permit",
        json={"device_credential_id": credential["payload"]["credential_id"]},
    )
    assert response.status_code == 403
