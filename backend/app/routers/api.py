from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.dependencies import CurrentUser, DbSession, StudentUser, TeacherUser
from app.models import (
    AttendanceClaim,
    AttendanceDecision,
    AuditEvent,
    DeviceCredential,
    Lesson,
    LessonMember,
    LessonPermit,
    User,
)
from app.schemas import (
    ClaimProof,
    ClaimSyncRequest,
    ClaimSyncResponse,
    ClaimSyncResult,
    DeviceEnrollRequest,
    LessonView,
    MockLoginRequest,
    PermitBundle,
    PermitRequest,
    SignedEnvelope,
    StartLessonRequest,
    UserView,
)
from app.security import (
    ALGORITHM,
    create_session_token,
    get_portal_signer,
    isoformat_z,
    public_key_from_jwk,
)
from app.services.proofs import ProofRejected, envelope_dict, validate_claim


router = APIRouter(prefix="/api/v1")


def _envelope(payload: dict, signature: str, key_id: str) -> SignedEnvelope:
    return SignedEnvelope(payload=payload, signature=signature, key_id=key_id, algorithm=ALGORITHM)


def _credential_envelope(record: DeviceCredential) -> SignedEnvelope:
    return _envelope(record.signed_payload, record.portal_signature, record.portal_key_id)


def _permit_envelope(record: LessonPermit) -> SignedEnvelope:
    return _envelope(record.signed_payload, record.portal_signature, record.portal_key_id)


def _lesson_state(lesson: Lesson, now: datetime) -> str:
    starts_at = lesson.starts_at.replace(tzinfo=lesson.starts_at.tzinfo or timezone.utc)
    ends_at = lesson.ends_at.replace(tzinfo=lesson.ends_at.tzinfo or timezone.utc)
    if now < starts_at:
        return "scheduled"
    if now <= ends_at:
        return "current"
    return "ended"


def _lesson_view(lesson: Lesson, now: datetime) -> LessonView:
    return LessonView(
        id=lesson.id,
        course_code=lesson.course_code,
        title=lesson.title,
        kind=lesson.kind,
        group_name=lesson.group_name,
        room=lesson.room,
        starts_at=lesson.starts_at,
        ends_at=lesson.ends_at,
        teacher_name=lesson.teacher.full_name,
        state=_lesson_state(lesson, now),
        test_managed=lesson.test_managed,
    )


async def _audit(db: DbSession, actor: str | None, event_type: str, subject: str | None, details: dict) -> None:
    db.add(
        AuditEvent(
            id=str(uuid4()),
            occurred_at=datetime.now(timezone.utc),
            actor_user_id=actor,
            event_type=event_type,
            subject_id=subject,
            details=details,
        )
    )


@router.get("/system/trust")
async def trust_anchor() -> dict:
    signer = get_portal_signer()
    return {"algorithm": ALGORITHM, "key_id": signer.key_id, "public_key_jwk": signer.public_jwk}


@router.get("/auth/mock/accounts", response_model=list[UserView])
async def mock_accounts(db: DbSession) -> list[User]:
    settings = get_settings()
    if not settings.enable_test_api:
        raise HTTPException(status_code=404, detail="Mock SSO is disabled")
    return list((await db.scalars(select(User).where(User.active.is_(True)).order_by(User.role.desc(), User.email))).all())


@router.post("/auth/mock/login", response_model=UserView)
async def mock_login(body: MockLoginRequest, response: Response, db: DbSession) -> User:
    settings = get_settings()
    if not settings.enable_test_api:
        raise HTTPException(status_code=404, detail="Mock SSO is disabled")
    user = await db.scalar(select(User).where(User.email == body.email.lower(), User.active.is_(True)))
    if user is None:
        raise HTTPException(status_code=401, detail="Unknown mock SSO account")
    token = create_session_token(user.id)
    response.set_cookie(
        "attendpro_session",
        token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=settings.session_expire_minutes * 60,
        path="/",
    )
    await _audit(db, user.id, "MOCK_SSO_LOGIN", user.id, {"provider": "mock-sso"})
    await db.commit()
    return user


@router.post("/auth/logout", status_code=204)
async def logout(response: Response) -> None:
    response.delete_cookie("attendpro_session", path="/")


@router.get("/auth/me", response_model=UserView)
async def me(user: CurrentUser) -> User:
    return user


@router.post("/devices/enroll", response_model=SignedEnvelope)
async def enroll_device(body: DeviceEnrollRequest, user: CurrentUser, db: DbSession) -> SignedEnvelope:
    try:
        UUID(body.device_id)
        public_key_from_jwk(body.public_key_jwk)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    existing = await db.scalar(select(DeviceCredential).where(DeviceCredential.device_id == body.device_id))
    if existing:
        if existing.user_id == user.id and existing.public_jwk == body.public_key_jwk and existing.revoked_at is None:
            return _credential_envelope(existing)
        raise HTTPException(status_code=409, detail="Device id is already registered")
    signer = get_portal_signer()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=get_settings().device_credential_days)
    credential_id = str(uuid4())
    payload = {
        "version": "attendpro.device-credential.v1",
        "credential_id": credential_id,
        "device_id": body.device_id,
        "user_id": user.id,
        "role": user.role,
        "public_key_jwk": body.public_key_jwk,
        "issued_at": isoformat_z(now),
        "expires_at": isoformat_z(expires_at),
    }
    signature = signer.sign(payload)
    credential = DeviceCredential(
        id=credential_id,
        device_id=body.device_id,
        user_id=user.id,
        label=body.label,
        public_jwk=body.public_key_jwk,
        issued_at=now,
        expires_at=expires_at,
        signed_payload=payload,
        portal_signature=signature,
        portal_key_id=signer.key_id,
    )
    db.add(credential)
    await _audit(db, user.id, "DEVICE_ENROLLED", credential.id, {"device_id": body.device_id})
    await db.commit()
    return _credential_envelope(credential)


@router.get("/schedule", response_model=list[LessonView])
async def schedule(user: CurrentUser, db: DbSession) -> list[LessonView]:
    lessons = list(
        (
            await db.scalars(
                select(Lesson)
                .options(selectinload(Lesson.teacher), selectinload(Lesson.members))
                .order_by(Lesson.starts_at)
            )
        ).unique().all()
    )
    visible = [
        lesson
        for lesson in lessons
        if lesson.teacher_id == user.id or any(member.student_id == user.id for member in lesson.members)
    ]
    now = datetime.now(timezone.utc)
    return [_lesson_view(lesson, now) for lesson in visible]


@router.get("/schedule/current", response_model=LessonView | None)
async def current_lesson(user: CurrentUser, db: DbSession) -> LessonView | None:
    lessons = await schedule(user, db)
    return next((lesson for lesson in lessons if lesson.state == "current"), None)


@router.post("/test/lessons/start-now", response_model=LessonView)
async def start_lesson_now(body: StartLessonRequest, teacher: TeacherUser, db: DbSession) -> LessonView:
    if not get_settings().enable_test_api:
        raise HTTPException(status_code=404, detail="Test API is disabled")
    query = select(Lesson).options(selectinload(Lesson.teacher)).where(
        Lesson.teacher_id == teacher.id, Lesson.test_managed.is_(True)
    )
    if body.lesson_id:
        query = query.where(Lesson.id == body.lesson_id)
    lesson = await db.scalar(query.order_by(Lesson.starts_at))
    if lesson is None:
        raise HTTPException(status_code=404, detail="Test lesson not found")
    now = datetime.now(timezone.utc)
    lesson.starts_at = now - timedelta(minutes=5)
    lesson.ends_at = now + timedelta(minutes=body.duration_minutes - 5)
    for permit in list(
        (await db.scalars(select(LessonPermit).where(LessonPermit.lesson_id == lesson.id, LessonPermit.revoked_at.is_(None)))).all()
    ):
        permit.revoked_at = now
    await _audit(db, teacher.id, "TEST_LESSON_STARTED", lesson.id, {"duration_minutes": body.duration_minutes})
    await db.commit()
    return _lesson_view(lesson, now)


@router.post("/lessons/{lesson_id}/permit", response_model=PermitBundle)
async def issue_permit(
    lesson_id: str, body: PermitRequest, teacher: TeacherUser, db: DbSession
) -> PermitBundle:
    lesson = await db.get(Lesson, lesson_id)
    credential = await db.get(DeviceCredential, body.device_credential_id)
    now = datetime.now(timezone.utc)
    if lesson is None or lesson.teacher_id != teacher.id:
        raise HTTPException(status_code=404, detail="Lesson not found for this teacher")
    if (
        credential is None
        or credential.user_id != teacher.id
        or credential.revoked_at is not None
        or credential.expires_at.replace(tzinfo=credential.expires_at.tzinfo or timezone.utc) <= now
    ):
        raise HTTPException(status_code=403, detail="Active teacher device credential required")
    existing = await db.scalar(
        select(LessonPermit).where(
            LessonPermit.lesson_id == lesson.id,
            LessonPermit.teacher_device_credential_id == credential.id,
            LessonPermit.revoked_at.is_(None),
            LessonPermit.expires_at > now,
        )
    )
    if existing:
        return PermitBundle(teacher_credential=_credential_envelope(credential), permit=_permit_envelope(existing))
    signer = get_portal_signer()
    permit_id = str(uuid4())
    not_before = lesson.starts_at.replace(tzinfo=lesson.starts_at.tzinfo or timezone.utc) - timedelta(hours=12)
    expires_at = lesson.ends_at.replace(tzinfo=lesson.ends_at.tzinfo or timezone.utc) + timedelta(hours=2)
    payload = {
        "version": "attendpro.lesson-permit.v1",
        "permit_id": permit_id,
        "lesson_id": lesson.id,
        "teacher_user_id": teacher.id,
        "teacher_device_credential_id": credential.id,
        "allowed_kinds": ["ENTRY", "EXIT"],
        "issued_at": isoformat_z(now),
        "not_before": isoformat_z(not_before),
        "expires_at": isoformat_z(expires_at),
    }
    signature = signer.sign(payload)
    permit = LessonPermit(
        id=permit_id,
        lesson_id=lesson.id,
        teacher_device_credential_id=credential.id,
        issued_at=now,
        not_before=not_before,
        expires_at=expires_at,
        signed_payload=payload,
        portal_signature=signature,
        portal_key_id=signer.key_id,
    )
    db.add(permit)
    await _audit(db, teacher.id, "LESSON_PERMIT_ISSUED", permit.id, {"lesson_id": lesson.id})
    await db.commit()
    return PermitBundle(teacher_credential=_credential_envelope(credential), permit=_permit_envelope(permit))


def _decision_envelope(claim_id: str, status: str, reason_code: str, evidence_hash: str) -> SignedEnvelope:
    signer = get_portal_signer()
    payload = {
        "version": "attendpro.portal-decision.v1",
        "decision_id": str(uuid4()),
        "claim_id": claim_id,
        "status": status,
        "reason_code": reason_code,
        "evidence_hash": evidence_hash,
        "decided_at": isoformat_z(datetime.now(timezone.utc)),
    }
    return _envelope(payload, signer.sign(payload), signer.key_id)


async def _sync_one(proof: ClaimProof, student: User, db: DbSession) -> ClaimSyncResult:
    from app.security import canonical_digest

    proof_dict = proof.model_dump(mode="json")
    evidence_hash = canonical_digest(proof_dict)
    requested_claim_id = str(proof.claim.payload.get("claim_id", "unknown"))
    if len(requested_claim_id) > 100:
        requested_claim_id = f"malformed-{evidence_hash}"
    existing = await db.scalar(
        select(AttendanceClaim)
        .options(selectinload(AttendanceClaim.decision))
        .where(AttendanceClaim.id == requested_claim_id)
    )
    if existing and existing.student_id == student.id and existing.decision:
        decision = existing.decision
        return ClaimSyncResult(
            claim_id=existing.id,
            decision=_envelope(decision.signed_payload, decision.portal_signature, decision.portal_key_id),
        )
    try:
        validated = await validate_claim(db, proof, student, datetime.now(timezone.utc))
        duplicate = await db.scalar(
            select(AttendanceClaim).where(
                AttendanceClaim.student_id == student.id,
                AttendanceClaim.lesson_id == validated.lesson_id,
                AttendanceClaim.kind == validated.kind,
            )
        )
        if duplicate:
            decision = _decision_envelope(validated.claim_id, "REJECTED", "DUPLICATE_ATTENDANCE", evidence_hash)
            return ClaimSyncResult(claim_id=validated.claim_id, decision=decision)
        decision = _decision_envelope(validated.claim_id, "ACCEPTED", "PROOF_VALID", evidence_hash)
        claim = AttendanceClaim(
            id=validated.claim_id,
            challenge_id=validated.challenge_id,
            lesson_id=validated.lesson_id,
            student_id=validated.student_id,
            student_device_credential_id=validated.student_device_credential_id,
            kind=validated.kind,
            captured_at=validated.captured_at,
            received_at=datetime.now(timezone.utc),
            proof=proof_dict,
            status="ACCEPTED",
            reason_code="PROOF_VALID",
            giper_document_id=",".join(proof.replica_refs)[:255] or None,
        )
        claim.decision = AttendanceDecision(
            id=str(decision.payload["decision_id"]),
            decided_at=datetime.now(timezone.utc),
            signed_payload=decision.payload,
            portal_signature=decision.signature,
            portal_key_id=decision.key_id,
        )
        db.add(claim)
        await _audit(db, student.id, "CLAIM_ACCEPTED", claim.id, {"lesson_id": claim.lesson_id, "kind": claim.kind})
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            decision = _decision_envelope(validated.claim_id, "REJECTED", "DUPLICATE_ATTENDANCE", evidence_hash)
        return ClaimSyncResult(claim_id=validated.claim_id, decision=decision)
    except ProofRejected as exc:
        decision = _decision_envelope(requested_claim_id, "REJECTED", exc.reason_code, evidence_hash)
        await _audit(db, student.id, "CLAIM_REJECTED", requested_claim_id, {"reason_code": exc.reason_code})
        await db.commit()
        return ClaimSyncResult(claim_id=requested_claim_id, decision=decision)


@router.post("/claims/sync", response_model=ClaimSyncResponse)
async def sync_claims(body: ClaimSyncRequest, student: StudentUser, db: DbSession) -> ClaimSyncResponse:
    results = [await _sync_one(proof, student, db) for proof in body.claims]
    return ClaimSyncResponse(results=results)


@router.get("/attendance/me")
async def my_attendance(student: StudentUser, db: DbSession) -> list[dict]:
    claims = list(
        (
            await db.scalars(
                select(AttendanceClaim)
                .where(AttendanceClaim.student_id == student.id)
                .order_by(AttendanceClaim.captured_at.desc())
            )
        ).all()
    )
    return [
        {
            "claim_id": claim.id,
            "lesson_id": claim.lesson_id,
            "kind": claim.kind,
            "captured_at": claim.captured_at,
            "received_at": claim.received_at,
            "status": claim.status,
            "reason_code": claim.reason_code,
            "giper_document_id": claim.giper_document_id,
        }
        for claim in claims
    ]


@router.get("/lessons/{lesson_id}/attendance")
async def lesson_attendance(lesson_id: str, teacher: TeacherUser, db: DbSession) -> list[dict]:
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None or lesson.teacher_id != teacher.id:
        raise HTTPException(status_code=404, detail="Lesson not found for this teacher")
    rows = (
        await db.execute(
            select(AttendanceClaim, User)
            .join(User, User.id == AttendanceClaim.student_id)
            .where(AttendanceClaim.lesson_id == lesson_id)
            .order_by(AttendanceClaim.captured_at)
        )
    ).all()
    return [
        {
            "claim_id": claim.id,
            "student_id": user.id,
            "student_name": user.full_name,
            "kind": claim.kind,
            "captured_at": claim.captured_at,
            "status": claim.status,
        }
        for claim, user in rows
    ]
