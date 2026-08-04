from sqlalchemy.dialects import postgresql

from app.models import Attendance, Schedule, ScheduleLecturer


def test_schedule_database_contract():
    assert Schedule.__tablename__ == "schedule"
    columns = set(Schedule.__table__.columns.keys())
    assert {
        "module",
        "short_name",
        "full_name",
        "type",
        "form",
        "group",
        "audience",
        "capacity",
        "equipment",
        "start_time",
        "end_time",
        "duration",
        "fact_passed",
        "students",
        "allowed_late_minutes",
        "attendance_started_at",
        "attendance_finished_at",
        "exit_enabled",
    } <= columns
    assert {
        "title",
        "discipline",
        "lesson_type",
        "room",
        "building",
        "starts_at",
        "ends_at",
    }.isdisjoint(columns)
    assert str(Schedule.start_time.type.compile(dialect=postgresql.dialect())) == (
        "TIMESTAMP WITH TIME ZONE"
    )
    assert str(Schedule.end_time.type.compile(dialect=postgresql.dialect())) == (
        "TIMESTAMP WITH TIME ZONE"
    )


def test_schedule_foreign_keys_target_singular_table():
    lecturer_fk = next(iter(ScheduleLecturer.__table__.c.schedule_id.foreign_keys))
    attendance_fk = next(iter(Attendance.__table__.c.schedule_id.foreign_keys))

    assert lecturer_fk.target_fullname == "schedule.id"
    assert attendance_fk.target_fullname == "schedule.id"
