from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserPublic(BaseModel):
    id: int
    email: str
    role: str
    full_name: str
    group: str | None

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class LecturerPublic(BaseModel):
    id: int
    full_name: str

    model_config = ConfigDict(from_attributes=True)


class ScheduleCard(BaseModel):
    id: int
    module: str
    short_name: str
    full_name: str
    type: str
    form: str
    group: str
    audience: str
    capacity: int
    equipment: str
    start_time: datetime
    end_time: datetime
    duration: str
    fact_passed: bool
    students: list[str]
    lecturers: list[LecturerPublic]
    active: bool
    attendance_active: bool
    allowed_late_minutes: int
    attendance_started_at: datetime | None
    attendance_finished_at: datetime | None
    exit_enabled: bool


class StartAttendanceRequest(BaseModel):
    allowed_late_minutes: int = Field(default=15, ge=0, le=180)
    exit_enabled: bool = False


class CodeResponse(BaseModel):
    code: str
    qr_code: str
    expires_in: int
    schedule_id: int
    expires_at: datetime
    rotation_seconds: int = 15


class StopResponse(BaseModel):
    schedule_id: int
    stopped_at: datetime


class MarkRequest(BaseModel):
    schedule_id: int
    code: str = Field(pattern=r"^\d{6}$")
    type: str = Field(default="entry", pattern=r"^entry$")


class MarkResponse(BaseModel):
    id: int
    schedule_id: int
    timestamp: datetime
    type: str
    late_minutes: int
    credited: bool
    schedule_name: str
    message: str


class AttendanceItem(BaseModel):
    id: int
    user_id: int
    student_name: str
    timestamp: datetime
    type: str
    late_minutes: int
    credited: bool


class HistoryItem(BaseModel):
    id: int
    schedule_id: int
    schedule_name: str
    start_time: datetime
    timestamp: datetime
    audience: str
    type: str
    late_minutes: int
    credited: bool
