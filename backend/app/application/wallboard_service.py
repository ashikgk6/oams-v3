from __future__ import annotations

from app.domain.protocols import Clock, UnitOfWork
from app.models import AttendanceStatus, PunchDirection
from app.schemas import WallboardOut, WallboardPerson


class WallboardError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class WallboardApplicationService:
    """Read model: uses precomputed attendance_days + last punch (no re-derive)."""

    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    def build(self, token: str) -> WallboardOut:
        if not self._uow.display_tokens.resolve_active(token):
            raise WallboardError("Invalid display token")

        settings = self._uow.settings.get_or_create()
        day = self._clock.today()
        now = self._clock.now()
        working = day.weekday() < 5 and self._uow.settings.is_holiday(day) is None

        days_by_user = {row.user_id: row for row in self._uow.attendance.list_for_date(day)}
        users = self._uow.users.list_active()

        in_now: list[WallboardPerson] = []
        late_today: list[WallboardPerson] = []
        on_leave: list[WallboardPerson] = []
        not_in: list[WallboardPerson] = []

        for user in users:
            row = days_by_user.get(user.id)
            status = row.status if row else (
                AttendanceStatus.absent if working else AttendanceStatus.weekend
            )
            person = WallboardPerson(
                name=user.name,
                team=user.team.name if user.team else None,
                in_time=row.first_in.strftime("%H:%M") if row and row.first_in else None,
                late_minutes=row.late_minutes if row else None,
            )

            if status == AttendanceStatus.on_leave:
                on_leave.append(WallboardPerson(name=user.name, team=person.team))
                continue

            last = self._uow.punches.last_for_user_day(user.id, day)
            if last and last.direction == PunchDirection.IN:
                in_now.append(person)
            if status == AttendanceStatus.late:
                late_today.append(person)
            if working and status == AttendanceStatus.absent:
                not_in.append(WallboardPerson(name=user.name, team=person.team))

        expected = len(users) - len(on_leave)
        return WallboardOut(
            office_name=settings.office_name,
            timezone=settings.timezone,
            date=day.isoformat(),
            clock=now.strftime("%H:%M:%S"),
            is_working_day=working,
            closed_message=None if working else "Office closed today",
            counts={
                "in_now": len(in_now),
                "expected": max(expected, 0),
                "on_leave": len(on_leave),
                "late": len(late_today),
                "not_in": len(not_in),
            },
            in_now=in_now,
            late_today=late_today,
            on_leave=on_leave,
            not_in=not_in,
        )
