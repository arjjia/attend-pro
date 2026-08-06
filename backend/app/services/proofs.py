from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import DeviceCredential, Lesson, LessonMember, LessonPermit, User
from app.schemas import ClaimProof, SignedEnvelope
from app.security import canonical_digest, parse_instant, verify_es256


@dataclass(frozen=True)
class ValidatedClaim:
    claim_id: str
    challenge_id: str
    lesson_id: str
    student_id: str
    student_device_credential_id: str
    kind: str
    captured_at: datetime


class ProofRejected(ValueError):
    def __init__(self, reason_code: str, message: str) -> None:
        super().__init__(message)
        self.reason_code = reason_code


def envelope_dict(envelope: SignedEnvelope) -> dict[str, Any]:
    return envelope.model_dump(mode="json")


def _required(payload: dict[str, Any], key: str) -> Any:
    try:
        return payload[key]
    except KeyError as exc:
        raise ProofRejected("MALFORMED_PROOF", f"Missing {key}") from exc


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=value.tzinfo or timezone.utc).astimezone(timezone.utc)


def _uuid(value: Any, field: str) -> str:
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ProofRejected("MALFORMED_PROOF", f"{field} must be a UUID") from exc


def _portal_envelope_valid(envelope: SignedEnvelope, expected_version: str) -> None:
    from app.security import get_portal_signer

    signer = get_portal_signer()
    if envelope.key_id != signer.key_id or not signer.verify(envelope.payload, envelope.signature):
        raise ProofRejected("INVALID_PORTAL_SIGNATURE", "Portal signature is invalid")
    if envelope.payload.get("version") != expected_version:
        raise ProofRejected("UNSUPPORTED_PROOF_VERSION", "Unsupported signed object version")


async def validate_claim(
    db: AsyncSession, proof: ClaimProof, authenticated_user: User, received_at: datetime
) -> ValidatedClaim:
    settings = get_settings()
    _portal_envelope_valid(proof.teacher_credential, "attendpro.device-credential.v1")
    _portal_envelope_valid(proof.student_credential, "attendpro.device-credential.v1")
    _portal_envelope_valid(proof.permit, "attendpro.lesson-permit.v1")

    teacher_credential_id = _uuid(
        _required(proof.teacher_credential.payload, "credential_id"), "teacher credential_id"
    )
    student_credential_id = _uuid(
        _required(proof.student_credential.payload, "credential_id"), "student credential_id"
    )
    permit_id = _uuid(_required(proof.permit.payload, "permit_id"), "permit_id")
    teacher_credential = await db.get(DeviceCredential, teacher_credential_id)
    student_credential = await db.get(DeviceCredential, student_credential_id)
    permit = await db.get(LessonPermit, permit_id)
    if not teacher_credential or not student_credential or not permit:
        raise ProofRejected("UNKNOWN_CREDENTIAL", "A credential or permit is unknown")
    for record, envelope in (
        (teacher_credential, proof.teacher_credential),
        (student_credential, proof.student_credential),
    ):
        if record.revoked_at or record.signed_payload != envelope.payload or record.portal_signature != envelope.signature:
            raise ProofRejected("REVOKED_OR_REPLACED_CREDENTIAL", "Credential is no longer active")
    if permit.revoked_at or permit.signed_payload != proof.permit.payload or permit.portal_signature != proof.permit.signature:
        raise ProofRejected("REVOKED_OR_REPLACED_PERMIT", "Lesson permit is no longer active")

    teacher_user = await db.get(User, teacher_credential.user_id)
    if not teacher_user or teacher_user.role != "teacher":
        raise ProofRejected("INVALID_TEACHER", "Teacher credential does not belong to a teacher")
    if authenticated_user.role != "student" or student_credential.user_id != authenticated_user.id:
        raise ProofRejected("WRONG_STUDENT", "Claim credential does not belong to this session")
    teacher_credential_links = {
        "credential_id": teacher_credential.id,
        "device_id": teacher_credential.device_id,
        "user_id": teacher_credential.user_id,
        "role": "teacher",
        "public_key_jwk": teacher_credential.public_jwk,
    }
    student_credential_links = {
        "credential_id": student_credential.id,
        "device_id": student_credential.device_id,
        "user_id": authenticated_user.id,
        "role": "student",
        "public_key_jwk": student_credential.public_jwk,
    }
    if any(proof.teacher_credential.payload.get(key) != value for key, value in teacher_credential_links.items()):
        raise ProofRejected("BROKEN_PROOF_CHAIN", "Teacher credential fields do not match its record")
    if any(proof.student_credential.payload.get(key) != value for key, value in student_credential_links.items()):
        raise ProofRejected("WRONG_STUDENT", "Signed student identity does not match this session")

    challenge = proof.challenge.payload
    claim = proof.claim.payload
    if challenge.get("version") != "attendpro.teacher-challenge.v1" or claim.get("version") != "attendpro.student-claim.v1":
        raise ProofRejected("UNSUPPORTED_PROOF_VERSION", "Unsupported challenge or claim version")
    teacher_jwk = _required(proof.teacher_credential.payload, "public_key_jwk")
    student_jwk = _required(proof.student_credential.payload, "public_key_jwk")
    if not verify_es256(teacher_jwk, challenge, proof.challenge.signature):
        raise ProofRejected("INVALID_TEACHER_SIGNATURE", "Teacher challenge signature is invalid")
    if proof.challenge.key_id != teacher_credential.device_id:
        raise ProofRejected("WRONG_SIGNING_DEVICE", "Challenge key id is not the teacher device")
    if not verify_es256(student_jwk, claim, proof.claim.signature):
        raise ProofRejected("INVALID_STUDENT_SIGNATURE", "Student claim signature is invalid")
    if proof.claim.key_id != student_credential.device_id:
        raise ProofRejected("WRONG_SIGNING_DEVICE", "Claim key id is not the student device")

    claim_id = _uuid(_required(claim, "claim_id"), "claim_id")
    challenge_id = _uuid(_required(challenge, "challenge_id"), "challenge_id")
    lesson_id = _uuid(_required(claim, "lesson_id"), "lesson_id")
    kind = str(_required(claim, "kind"))
    if kind not in {"ENTRY", "EXIT"}:
        raise ProofRejected("INVALID_ATTENDANCE_KIND", "Only ENTRY and EXIT are supported")
    expected_digest = canonical_digest(envelope_dict(proof.challenge))
    if claim.get("challenge_digest") != expected_digest:
        raise ProofRejected("CHALLENGE_NOT_BOUND", "Claim is not bound to this exact challenge")
    expected_links = {
        "lesson_id": lesson_id,
        "kind": kind,
        "challenge_id": challenge_id,
        "student_device_id": student_credential.device_id,
        "student_user_id": authenticated_user.id,
    }
    for field, expected in expected_links.items():
        source = challenge if field in {"lesson_id", "kind", "challenge_id"} else claim
        if source.get(field) != expected:
            raise ProofRejected("BROKEN_PROOF_CHAIN", f"Mismatched {field}")
    if challenge.get("permit_id") != permit.id or challenge.get("teacher_device_id") != teacher_credential.device_id:
        raise ProofRejected("BROKEN_PROOF_CHAIN", "Challenge is not bound to its permit and teacher device")
    if proof.permit.payload.get("lesson_id") != lesson_id:
        raise ProofRejected("BROKEN_PROOF_CHAIN", "Permit belongs to a different lesson")
    if proof.permit.payload.get("teacher_device_credential_id") != teacher_credential.id:
        raise ProofRejected("BROKEN_PROOF_CHAIN", "Permit belongs to a different teacher credential")
    if proof.permit.payload.get("teacher_user_id") != teacher_user.id:
        raise ProofRejected("BROKEN_PROOF_CHAIN", "Permit belongs to a different teacher")
    if kind not in proof.permit.payload.get("allowed_kinds", []):
        raise ProofRejected("ATTENDANCE_KIND_NOT_PERMITTED", "Permit does not allow this attendance kind")

    lesson = await db.get(Lesson, permit.lesson_id)
    if lesson is None:
        raise ProofRejected("UNKNOWN_LESSON", "Lesson no longer exists")
    if lesson.id != lesson_id or lesson.teacher_id != teacher_user.id:
        raise ProofRejected("TEACHER_NOT_ASSIGNED", "Teacher is not assigned to this lesson")
    membership = await db.scalar(
        select(LessonMember).where(
            LessonMember.lesson_id == lesson_id, LessonMember.student_id == authenticated_user.id
        )
    )
    if membership is None:
        raise ProofRejected("STUDENT_NOT_ENROLLED", "Student is not enrolled in this lesson")

    try:
        captured_at = parse_instant(str(_required(claim, "captured_at")))
        challenge_issued_at = parse_instant(str(_required(challenge, "issued_at")))
        challenge_expires_at = parse_instant(str(_required(challenge, "expires_at")))
    except ValueError as exc:
        raise ProofRejected("INVALID_TIME", str(exc)) from exc
    skew = timedelta(seconds=settings.clock_skew_seconds)
    if challenge_expires_at <= challenge_issued_at or challenge_expires_at - challenge_issued_at > timedelta(
        seconds=settings.qr_ttl_seconds
    ):
        raise ProofRejected("INVALID_QR_LIFETIME", "QR challenge lifetime is invalid")
    if captured_at < challenge_issued_at - skew or captured_at > challenge_expires_at + skew:
        raise ProofRejected("QR_EXPIRED_AT_CAPTURE", "QR was not valid when the claim was captured")
    if captured_at > received_at + skew:
        raise ProofRejected("CLOCK_TOO_FAR_AHEAD", "Student clock is too far ahead")
    if challenge_issued_at > received_at + skew:
        raise ProofRejected("CLOCK_TOO_FAR_AHEAD", "Teacher clock is too far ahead")
    if captured_at < _utc(teacher_credential.issued_at) - skew or captured_at > _utc(
        teacher_credential.expires_at
    ) + skew:
        raise ProofRejected("TEACHER_CREDENTIAL_EXPIRED", "Teacher credential was not valid at capture time")
    if captured_at < _utc(student_credential.issued_at) - skew or captured_at > _utc(
        student_credential.expires_at
    ) + skew:
        raise ProofRejected("STUDENT_CREDENTIAL_EXPIRED", "Student credential was not valid at capture time")
    if captured_at < _utc(permit.not_before) - skew or captured_at > _utc(permit.expires_at) + skew:
        raise ProofRejected("PERMIT_EXPIRED_AT_CAPTURE", "Lesson permit was not valid at capture time")
    if captured_at < _utc(lesson.starts_at) - timedelta(minutes=15) or captured_at > _utc(
        lesson.ends_at
    ) + timedelta(minutes=15):
        raise ProofRejected("OUTSIDE_LESSON_WINDOW", "Claim was captured outside the lesson window")

    return ValidatedClaim(
        claim_id=claim_id,
        challenge_id=challenge_id,
        lesson_id=lesson_id,
        student_id=authenticated_user.id,
        student_device_credential_id=student_credential.id,
        kind=kind,
        captured_at=captured_at,
    )
