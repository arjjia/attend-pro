from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(20), index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    group_name: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    taught_lessons: Mapped[list[Lesson]] = relationship(back_populates="teacher")
    memberships: Mapped[list[LessonMember]] = relationship(back_populates="student")
    devices: Mapped[list[DeviceCredential]] = relationship(back_populates="user")


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    course_code: Mapped[str] = mapped_column(String(50), index=True)
    title: Mapped[str] = mapped_column(String(500))
    kind: Mapped[str] = mapped_column(String(100), default="Практическое занятие")
    group_name: Mapped[str] = mapped_column(String(100), index=True)
    room: Mapped[str] = mapped_column(String(255))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    teacher_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    test_managed: Mapped[bool] = mapped_column(Boolean, default=False)

    teacher: Mapped[User] = relationship(back_populates="taught_lessons")
    members: Mapped[list[LessonMember]] = relationship(
        back_populates="lesson", cascade="all, delete-orphan"
    )
    permits: Mapped[list[LessonPermit]] = relationship(back_populates="lesson")


class LessonMember(Base):
    __tablename__ = "lesson_members"

    lesson_id: Mapped[str] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"), primary_key=True
    )
    student_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    lesson: Mapped[Lesson] = relationship(back_populates="members")
    student: Mapped[User] = relationship(back_populates="memberships")


class DeviceCredential(Base):
    __tablename__ = "device_credentials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    device_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    label: Mapped[str] = mapped_column(String(120))
    public_jwk: Mapped[dict] = mapped_column(JSON)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    signed_payload: Mapped[dict] = mapped_column(JSON)
    portal_signature: Mapped[str] = mapped_column(Text)
    portal_key_id: Mapped[str] = mapped_column(String(100))

    user: Mapped[User] = relationship(back_populates="devices")


class LessonPermit(Base):
    __tablename__ = "lesson_permits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    lesson_id: Mapped[str] = mapped_column(ForeignKey("lessons.id"), index=True)
    teacher_device_credential_id: Mapped[str] = mapped_column(
        ForeignKey("device_credentials.id"), index=True
    )
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    not_before: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    signed_payload: Mapped[dict] = mapped_column(JSON)
    portal_signature: Mapped[str] = mapped_column(Text)
    portal_key_id: Mapped[str] = mapped_column(String(100))

    lesson: Mapped[Lesson] = relationship(back_populates="permits")
    teacher_device: Mapped[DeviceCredential] = relationship()


class AttendanceClaim(Base):
    __tablename__ = "attendance_claims"
    __table_args__ = (
        UniqueConstraint(
            "student_id", "lesson_id", "kind", name="uq_claim_student_lesson_kind"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    challenge_id: Mapped[str] = mapped_column(String(36), index=True)
    lesson_id: Mapped[str] = mapped_column(ForeignKey("lessons.id"), index=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    student_device_credential_id: Mapped[str] = mapped_column(
        ForeignKey("device_credentials.id"), index=True
    )
    kind: Mapped[str] = mapped_column(String(10))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    proof: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), index=True)
    reason_code: Mapped[str] = mapped_column(String(80))
    giper_document_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    decision: Mapped[AttendanceDecision | None] = relationship(
        back_populates="claim", uselist=False, cascade="all, delete-orphan"
    )


class AttendanceDecision(Base):
    __tablename__ = "attendance_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    claim_id: Mapped[str] = mapped_column(
        ForeignKey("attendance_claims.id", ondelete="CASCADE"), unique=True, index=True
    )
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    signed_payload: Mapped[dict] = mapped_column(JSON)
    portal_signature: Mapped[str] = mapped_column(Text)
    portal_key_id: Mapped[str] = mapped_column(String(100))

    claim: Mapped[AttendanceClaim] = relationship(back_populates="decision")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    actor_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    subject_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
