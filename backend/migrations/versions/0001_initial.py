"""Initial AttendPro schema.

Revision ID: 0001
Revises:
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("group", sa.String(length=100), nullable=True),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_role", "users", ["role"])
    op.create_index("ix_users_group", "users", ["group"])

    op.create_table(
        "schedule",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("module", sa.String(length=255), nullable=False),
        sa.Column("short_name", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=500), nullable=False),
        sa.Column("type", sa.String(length=100), nullable=False),
        sa.Column("form", sa.String(length=100), nullable=False),
        sa.Column("group", sa.String(length=100), nullable=False),
        sa.Column("audience", sa.String(length=255), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("equipment", sa.String(length=255), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration", sa.String(length=50), nullable=False),
        sa.Column("fact_passed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("students", sa.JSON(), nullable=False),
        sa.Column("allowed_late_minutes", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("attendance_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attendance_finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exit_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_schedule_group", "schedule", ["group"])
    op.create_index("ix_schedule_start_time", "schedule", ["start_time"])
    op.create_index("ix_schedule_end_time", "schedule", ["end_time"])

    op.create_table(
        "schedule_lecturers",
        sa.Column(
            "schedule_id",
            sa.Integer(),
            sa.ForeignKey("schedule.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "lecturer_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_table(
        "attendance",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "schedule_id",
            sa.Integer(),
            sa.ForeignKey("schedule.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("late_minutes", sa.Integer(), nullable=False),
        sa.Column("is_credited", sa.Boolean(), nullable=False),
        sa.UniqueConstraint(
            "user_id", "schedule_id", "type", name="uq_attendance_user_schedule_type"
        ),
    )
    op.create_index("ix_attendance_user_id", "attendance", ["user_id"])
    op.create_index("ix_attendance_schedule_id", "attendance", ["schedule_id"])
    op.create_index("ix_attendance_timestamp", "attendance", ["timestamp"])


def downgrade() -> None:
    op.drop_table("attendance")
    op.drop_table("schedule_lecturers")
    op.drop_table("schedule")
    op.drop_table("users")
