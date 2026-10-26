from __future__ import annotations

from datetime import date, timedelta

from app.domain.attendance.policy import DefaultAttendancePolicy
from app.domain.clock import IstClock
from app.domain.protocols import AttendancePolicy, Clock, UnitOfWork
from app.models import (
    AttendanceDay,
    AttendanceStatus,
    PunchCorrection,
    PunchDirection,
    PunchEvent,
    User,
    UserRole,
)


class AttendanceApplicationService:
    def __init__(
        self,
        uow: UnitOfWork,
        policy: AttendancePolicy | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._uow = uow
        self._policy = policy or DefaultAttendancePolicy()
        self._clock = clock or IstClock()

    def derive_for_user(self, user: User, day: date, *, finalize: bool = False) -> AttendanceDay:
        settings = self._uow.settings.get_or_create()
        snap = self._policy.evaluate(
            day=day,
            settings=settings,
            events=self._uow.punches.list_for_user_day(user.id, day),
            on_leave=self._uow.leave.approved_on(user.id, day) is not None,
            is_holiday=self._uow.settings.is_holiday(day) is not None,
            is_weekend=day.weekday() >= 5,
        )

        existing = self._uow.attendance.get(user.id, day, for_update=True)
        if existing:
            # Finalized weekend/holiday rows are frozen — punches on those days are ignored.
            if existing.finalized and existing.status in (
                AttendanceStatus.weekend,
                AttendanceStatus.holiday,
            ):
                return existing
            existing.status = snap.status
            existing.first_in = snap.first_in
            existing.last_out = snap.last_out
            existing.work_minutes = snap.work_minutes
            existing.late_minutes = snap.late_minutes
            if finalize:
                existing.finalized = True
            return self._uow.attendance.upsert(existing)

        return self._uow.attendance.upsert(
            AttendanceDay(
                user_id=user.id,
                date=day,
                status=snap.status,
                first_in=snap.first_in,
                last_out=snap.last_out,
                work_minutes=snap.work_minutes,
                late_minutes=snap.late_minutes,
                finalized=finalize,
                version=1,
            )
        )

    def recompute_user_day(self, user_id: int, day: date) -> AttendanceDay:
        user = self._uow.users.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        row = self.derive_for_user(user, day)
        self._uow.commit()
        self._uow.refresh(row)
        return row

    def next_direction(self, user_id: int, day: date) -> PunchDirection:
        last = self._uow.punches.last_for_user_day(user_id, day)
        if last is None or last.direction == PunchDirection.OUT:
            return PunchDirection.IN
        return PunchDirection.OUT

    def apply_correction(self, correction: PunchCorrection) -> None:
        self._uow.punches.delete_for_user_day(correction.user_id, correction.date)
        if correction.requested_in:
            self._uow.punches.add(
                PunchEvent(
                    user_id=correction.user_id,
                    direction=PunchDirection.IN,
                    ts=correction.requested_in,
                    source="correction",
                )
            )
        if correction.requested_out:
            self._uow.punches.add(
                PunchEvent(
                    user_id=correction.user_id,
                    direction=PunchDirection.OUT,
                    ts=correction.requested_out,
                    source="correction",
                )
            )
        user = self._uow.users.get_by_id(correction.user_id)
        if not user:
            raise ValueError("User not found for correction")
        self.derive_for_user(user, correction.date)
        self._uow.commit()

    def finalize_day(self, day: date | None = None) -> dict:
        target = day or self._clock.today()
        users = self._uow.users.list_active()
        counts = {s.value: 0 for s in AttendanceStatus}
        for user in users:
            row = self.derive_for_user(user, target, finalize=True)
            counts[row.status.value] = counts.get(row.status.value, 0) + 1
        self._uow.audit.record("day.finalize", None, {"date": str(target), "users": len(users)})
        self._uow.commit()
        return {"date": str(target), "counts": counts, "users": len(users)}

    def recompute_all(self, day: date | None = None) -> dict:
        target = day or self._clock.today()
        users = self._uow.users.list_active()
        for user in users:
            self.derive_for_user(user, target)
        self._uow.commit()
        return {"ok": True, "date": str(target), "users": len(users)}

    def my_history(self, user: User, days: int = 30) -> list[AttendanceDay]:
        end = self._clock.today()
        start = end - timedelta(days=days - 1)
        self.derive_for_user(user, end)
        self._uow.commit()
        return self._uow.attendance.list_for_user_range(user.id, start, end)

    def managed_team_ids(self, manager: User) -> list[int]:
        team_ids = [t.id for t in self._uow.teams.list_managed_by(manager.id)]
        if manager.team_id and manager.team_id not in team_ids:
            team_ids.append(manager.team_id)
        return team_ids

    def scoped_active_user_ids(self, actor: User) -> list[int] | None:
        """None means admin/unscoped (all users)."""
        if actor.role == UserRole.admin:
            return None
        return [
            u.id
            for u in self._uow.users.list_active(team_ids=self.managed_team_ids(actor))
        ]

    def office_today(self, actor: User) -> dict:
        d = self._clock.today()
        team_ids = (
            self.managed_team_ids(actor) if actor.role == UserRole.manager else None
        )
        members = []
        for u in self._uow.users.list_active(team_ids=team_ids):
            row = self.derive_for_user(u, d)
            members.append(
                {
                    "user_id": u.id,
                    "name": u.name,
                    "team": u.team.name if u.team else None,
                    "status": row.status.value,
                    "first_in": row.first_in.isoformat() if row.first_in else None,
                    "last_out": row.last_out.isoformat() if row.last_out else None,
                    "late_minutes": row.late_minutes,
                    "work_minutes": row.work_minutes,
                }
            )
        self._uow.commit()
        return {"date": str(d), "members": members}
