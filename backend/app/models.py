from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    group: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    taught_schedules: Mapped[list["Schedule"]] = relationship(
        secondary="schedule_lecturers", back_populates="lecturers"
    )
    attendance: Mapped[list["Attendance"]] = relationship(back_populates="user")


class ScheduleLecturer(Base):
    __tablename__ = "schedule_lecturers"

    schedule_id: Mapped[int] = mapped_column(
        ForeignKey("schedule.id", ondelete="CASCADE"), primary_key=True
    )
    lecturer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )


class Schedule(Base):
    __tablename__ = "schedule"

    id: Mapped[int] = mapped_column(primary_key=True)
    module: Mapped[str] = mapped_column(String(255))
    short_name: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(500))
    type: Mapped[str] = mapped_column(String(100))
    form: Mapped[str] = mapped_column(String(100))
    group: Mapped[str] = mapped_column(String(100), index=True)
    audience: Mapped[str] = mapped_column(String(255))
    capacity: Mapped[int] = mapped_column(Integer)
    equipment: Mapped[str] = mapped_column(String(255))
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    duration: Mapped[str] = mapped_column(String(50))
    fact_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    students: Mapped[list[str]] = mapped_column(JSON, default=list)
    allowed_late_minutes: Mapped[int] = mapped_column(Integer, default=15)
    attendance_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attendance_finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    exit_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    lecturers: Mapped[list[User]] = relationship(
        secondary="schedule_lecturers", back_populates="taught_schedules"
    )
    attendance: Mapped[list["Attendance"]] = relationship(
        back_populates="schedule", cascade="all, delete-orphan"
    )


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (
        UniqueConstraint("user_id", "schedule_id", "type", name="uq_attendance_user_schedule_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    schedule_id: Mapped[int] = mapped_column(
        ForeignKey("schedule.id", ondelete="CASCADE"), index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    type: Mapped[str] = mapped_column(String(20), default="entry")
    late_minutes: Mapped[int] = mapped_column(Integer, default=0)
    is_credited: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped[User] = relationship(back_populates="attendance")
    schedule: Mapped[Schedule] = relationship(back_populates="attendance")
