from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class UserView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    role: Literal["student", "teacher"]
    full_name: str
    group_name: str | None


class MockLoginRequest(BaseModel):
    email: str


class SignedEnvelope(BaseModel):
    payload: dict[str, Any]
    signature: str
    key_id: str
    algorithm: Literal["ES256"] = "ES256"


class DeviceEnrollRequest(BaseModel):
    device_id: str = Field(min_length=36, max_length=36)
    label: str = Field(min_length=1, max_length=120)
    public_key_jwk: dict[str, Any]


class LessonView(BaseModel):
    id: str
    course_code: str
    title: str
    kind: str
    group_name: str
    room: str
    starts_at: datetime
    ends_at: datetime
    teacher_name: str
    state: Literal["scheduled", "current", "ended"]
    test_managed: bool


class StartLessonRequest(BaseModel):
    lesson_id: str | None = None
    duration_minutes: int = Field(default=90, ge=15, le=240)


class PermitRequest(BaseModel):
    device_credential_id: str


class PermitBundle(BaseModel):
    teacher_credential: SignedEnvelope
    permit: SignedEnvelope


class ClaimProof(BaseModel):
    teacher_credential: SignedEnvelope
    permit: SignedEnvelope
    challenge: SignedEnvelope
    student_credential: SignedEnvelope
    claim: SignedEnvelope
    replica_refs: list[Annotated[str, Field(max_length=255)]] = Field(
        default_factory=list, max_length=5
    )


class ClaimSyncRequest(BaseModel):
    claims: list[ClaimProof] = Field(min_length=1, max_length=100)


class ClaimSyncResult(BaseModel):
    claim_id: str
    decision: SignedEnvelope


class ClaimSyncResponse(BaseModel):
    results: list[ClaimSyncResult]
