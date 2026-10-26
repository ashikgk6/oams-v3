from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from app.domain.attendance.policy import DefaultAttendancePolicy
from app.models import AttendanceStatus, OfficeSettings, PunchDirection, PunchEvent

IST = ZoneInfo("Asia/Kolkata")


def _settings() -> OfficeSettings:
    return OfficeSettings(
        office_name="Test",
        timezone="Asia/Kolkata",
        shift_start=time(9, 30),
        shift_end=time(18, 30),
        grace_minutes=15,
        half_day_after=time(13, 30),
        min_half_day_minutes=240,
    )


def _punch(direction: PunchDirection, hour: int, minute: int = 0) -> PunchEvent:
    day = date(2026, 8, 3)  # Monday
    return PunchEvent(
        user_id=1,
        direction=direction,
        ts=datetime(2026, 8, 3, hour, minute, tzinfo=IST),
        source="test",
    )


def test_present_within_grace():
    policy = DefaultAttendancePolicy()
    snap = policy.evaluate(
        day=date(2026, 8, 3),
        settings=_settings(),
        events=[_punch(PunchDirection.IN, 9, 40)],
        on_leave=False,
        is_holiday=False,
        is_weekend=False,
    )
    assert snap.status == AttendanceStatus.present
    assert snap.late_minutes == 0


def test_late_after_grace():
    policy = DefaultAttendancePolicy()
    snap = policy.evaluate(
        day=date(2026, 8, 3),
        settings=_settings(),
        events=[_punch(PunchDirection.IN, 10, 0)],
        on_leave=False,
        is_holiday=False,
        is_weekend=False,
    )
    assert snap.status == AttendanceStatus.late
    assert snap.late_minutes == 30


def test_half_day_late_arrival():
    policy = DefaultAttendancePolicy()
    snap = policy.evaluate(
        day=date(2026, 8, 3),
        settings=_settings(),
        events=[_punch(PunchDirection.IN, 14, 0)],
        on_leave=False,
        is_holiday=False,
        is_weekend=False,
    )
    assert snap.status == AttendanceStatus.half_day


def test_absent_without_punch():
    policy = DefaultAttendancePolicy()
    snap = policy.evaluate(
        day=date(2026, 8, 3),
        settings=_settings(),
        events=[],
        on_leave=False,
        is_holiday=False,
        is_weekend=False,
    )
    assert snap.status == AttendanceStatus.absent


def test_on_leave_overrides_punches():
    policy = DefaultAttendancePolicy()
    snap = policy.evaluate(
        day=date(2026, 8, 3),
        settings=_settings(),
        events=[_punch(PunchDirection.IN, 9, 30)],
        on_leave=True,
        is_holiday=False,
        is_weekend=False,
    )
    assert snap.status == AttendanceStatus.on_leave


def test_weekend():
    policy = DefaultAttendancePolicy()
    snap = policy.evaluate(
        day=date(2026, 8, 1),  # Saturday
        settings=_settings(),
        events=[],
        on_leave=False,
        is_holiday=False,
        is_weekend=True,
    )
    assert snap.status == AttendanceStatus.weekend


def test_short_day_becomes_half_day():
    policy = DefaultAttendancePolicy()
    snap = policy.evaluate(
        day=date(2026, 8, 3),
        settings=_settings(),
        events=[
            _punch(PunchDirection.IN, 9, 30),
            _punch(PunchDirection.OUT, 11, 0),
        ],
        on_leave=False,
        is_holiday=False,
        is_weekend=False,
    )
    assert snap.status == AttendanceStatus.half_day
    assert snap.work_minutes == 90
