"""Replace the prototype schema with the signed local-first MVP schema.

Revision ID: 0002
Revises: 0001

The previous repository only contained disposable fixture data and used integer
identities. There is no safe identity mapping to the new UUID/SSO model, so this
development migration intentionally replaces those prototype tables.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("attendance")
    op.drop_table("schedule_lecturers")
    op.drop_table("schedule")
    op.drop_table("users")

    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("group_name", sa.String(100), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_role", "users", ["role"])
    op.create_index("ix_users_group_name", "users", ["group_name"])
    op.create_table(
        "lessons",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("course_code", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("kind", sa.String(100), nullable=False),
        sa.Column("group_name", sa.String(100), nullable=False),
        sa.Column("room", sa.String(255), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("teacher_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("test_managed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    for name, columns in (
        ("ix_lessons_course_code", ["course_code"]),
        ("ix_lessons_group_name", ["group_name"]),
        ("ix_lessons_starts_at", ["starts_at"]),
        ("ix_lessons_ends_at", ["ends_at"]),
        ("ix_lessons_teacher_id", ["teacher_id"]),
    ):
        op.create_index(name, "lessons", columns)
    op.create_table(
        "lesson_members",
        sa.Column("lesson_id", sa.String(36), sa.ForeignKey("lessons.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("student_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "device_credentials",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("device_id", sa.String(36), nullable=False, unique=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("public_jwk", sa.JSON(), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("signed_payload", sa.JSON(), nullable=False),
        sa.Column("portal_signature", sa.Text(), nullable=False),
        sa.Column("portal_key_id", sa.String(100), nullable=False),
    )
    op.create_index("ix_device_credentials_device_id", "device_credentials", ["device_id"])
    op.create_index("ix_device_credentials_user_id", "device_credentials", ["user_id"])
    op.create_table(
        "lesson_permits",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("lesson_id", sa.String(36), sa.ForeignKey("lessons.id"), nullable=False),
        sa.Column("teacher_device_credential_id", sa.String(36), sa.ForeignKey("device_credentials.id"), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("not_before", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("signed_payload", sa.JSON(), nullable=False),
        sa.Column("portal_signature", sa.Text(), nullable=False),
        sa.Column("portal_key_id", sa.String(100), nullable=False),
    )
    op.create_index("ix_lesson_permits_lesson_id", "lesson_permits", ["lesson_id"])
    op.create_index("ix_lesson_permits_teacher_device_credential_id", "lesson_permits", ["teacher_device_credential_id"])
    op.create_table(
        "attendance_claims",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("challenge_id", sa.String(36), nullable=False),
        sa.Column("lesson_id", sa.String(36), sa.ForeignKey("lessons.id"), nullable=False),
        sa.Column("student_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("student_device_credential_id", sa.String(36), sa.ForeignKey("device_credentials.id"), nullable=False),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("proof", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("reason_code", sa.String(80), nullable=False),
        sa.Column("giper_document_id", sa.String(255), nullable=True),
        sa.UniqueConstraint("student_id", "lesson_id", "kind", name="uq_claim_student_lesson_kind"),
    )
    for name, columns in (
        ("ix_attendance_claims_challenge_id", ["challenge_id"]),
        ("ix_attendance_claims_lesson_id", ["lesson_id"]),
        ("ix_attendance_claims_student_id", ["student_id"]),
        ("ix_attendance_claims_student_device_credential_id", ["student_device_credential_id"]),
        ("ix_attendance_claims_captured_at", ["captured_at"]),
        ("ix_attendance_claims_received_at", ["received_at"]),
        ("ix_attendance_claims_status", ["status"]),
    ):
        op.create_index(name, "attendance_claims", columns)
    op.create_table(
        "attendance_decisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("claim_id", sa.String(36), sa.ForeignKey("attendance_claims.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("signed_payload", sa.JSON(), nullable=False),
        sa.Column("portal_signature", sa.Text(), nullable=False),
        sa.Column("portal_key_id", sa.String(100), nullable=False),
    )
    op.create_index("ix_attendance_decisions_claim_id", "attendance_decisions", ["claim_id"])
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_user_id", sa.String(36), nullable=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("subject_id", sa.String(100), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
    )
    op.create_index("ix_audit_events_occurred_at", "audit_events", ["occurred_at"])
    op.create_index("ix_audit_events_actor_user_id", "audit_events", ["actor_user_id"])
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])


def downgrade() -> None:
    raise NotImplementedError(
        "0002 intentionally replaces disposable prototype identities and cannot be downgraded; "
        "restore a database backup or recreate the development volume"
    )
