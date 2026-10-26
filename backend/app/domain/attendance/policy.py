from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Optional, Protocol, Sequence

from app.domain.clock import IST
from app.models import AttendanceStatus, OfficeSettings, PunchDirection, PunchEvent


def combine_ist(d: date, t: time) -> datetime:
    return datetime.combine(d, t, tzinfo=IST)


@dataclass(frozen=True)
class AttendanceSnapshot:
    status: AttendanceStatus
    first_in: Optional[datetime] = None
    last_out: Optional[datetime] = None
    work_minutes: Optional[int] = None
    late_minutes: Optional[int] = None


class WorkMinutesCalculator:
    """Sums completed IN→OUT pairs; ignores an open IN with no OUT."""

    def compute(self, events: Sequence[PunchEvent]) -> Optional[int]:
        total = 0
        open_in: Optional[datetime] = None
        paired = False
        for ev in sorted(events, key=lambda e: e.ts):
            if ev.direction == PunchDirection.IN:
                open_in = ev.ts
            elif ev.direction == PunchDirection.OUT and open_in is not None:
                delta = int((ev.ts - open_in).total_seconds() // 60)
                if delta > 0:
                    total += delta
                    paired = True
                open_in = None
        return total if paired else None


class DayClassifier:
    def classify(
        self, *, is_weekend: bool, is_holiday: bool, on_leave: bool
    ) -> Optional[AttendanceStatus]:
        if is_weekend:
            return AttendanceStatus.weekend
        if is_holiday:
            return AttendanceStatus.holiday
        if on_leave:
            return AttendanceStatus.on_leave
        return None


class PresenceStatusRule(Protocol):
    def apply(
        self,
        *,
        first_in: datetime,
        settings: OfficeSettings,
        day: date,
        work_minutes: Optional[int],
        current: AttendanceSnapshot,
    ) -> AttendanceSnapshot: ...


class LateOrPresentRule:
    def apply(
        self,
        *,
        first_in: datetime,
        settings: OfficeSettings,
        day: date,
        work_minutes: Optional[int],
        current: AttendanceSnapshot,
    ) -> AttendanceSnapshot:
        shift_start = combine_ist(day, settings.shift_start)
        deadline = shift_start + timedelta(minutes=settings.grace_minutes)
        half_after = combine_ist(day, settings.half_day_after)
        late_minutes = int((first_in - shift_start).total_seconds() // 60)

        if first_in > half_after:
            status = AttendanceStatus.half_day
        elif first_in > deadline:
            status = AttendanceStatus.late
        else:
            status = AttendanceStatus.present
            late_minutes = 0

        return AttendanceSnapshot(
            status=status,
            first_in=current.first_in,
            last_out=current.last_out,
            work_minutes=work_minutes,
            late_minutes=late_minutes,
        )


class ShortDayHalfDayRule:
    """Half-day when worked minutes fall below office minimum."""

    def apply(
        self,
        *,
        first_in: datetime,
        settings: OfficeSettings,
        day: date,
        work_minutes: Optional[int],
        current: AttendanceSnapshot,
    ) -> AttendanceSnapshot:
        if (
            work_minutes is not None
            and work_minutes < settings.min_half_day_minutes
            and current.status in (AttendanceStatus.present, AttendanceStatus.late)
        ):
            return AttendanceSnapshot(
                status=AttendanceStatus.half_day,
                first_in=current.first_in,
                last_out=current.last_out,
                work_minutes=work_minutes,
                late_minutes=current.late_minutes,
            )
        return current


class DefaultAttendancePolicy:
    """
    Calendar outcome first; otherwise run presence rules in order.
    Inject `presence_rules` to extend without editing this class.
    """

    def __init__(
        self,
        work_minutes: Optional[WorkMinutesCalculator] = None,
        classifier: Optional[DayClassifier] = None,
        presence_rules: Optional[Sequence[PresenceStatusRule]] = None,
    ) -> None:
        self._work = work_minutes or WorkMinutesCalculator()
        self._classifier = classifier or DayClassifier()
        self._rules: Sequence[PresenceStatusRule] = presence_rules or (
            LateOrPresentRule(),
            ShortDayHalfDayRule(),
        )

    def evaluate(
        self,
        *,
        day: date,
        settings: OfficeSettings,
        events: Sequence[PunchEvent],
        on_leave: bool,
        is_holiday: bool,
        is_weekend: bool,
    ) -> AttendanceSnapshot:
        calendar = self._classifier.classify(
            is_weekend=is_weekend, is_holiday=is_holiday, on_leave=on_leave
        )
        if calendar is not None:
            return AttendanceSnapshot(status=calendar)

        ins = [e for e in events if e.direction == PunchDirection.IN]
        outs = [e for e in events if e.direction == PunchDirection.OUT]
        first_in = ins[0].ts if ins else None
        last_out = outs[-1].ts if outs else None
        work_minutes = self._work.compute(events)

        if not first_in:
            working = not is_weekend and not is_holiday
            status = AttendanceStatus.absent if working else AttendanceStatus.weekend
            return AttendanceSnapshot(status=status)

        snap = AttendanceSnapshot(
            status=AttendanceStatus.present,
            first_in=first_in,
            last_out=last_out,
            work_minutes=work_minutes,
            late_minutes=0,
        )
        for rule in self._rules:
            snap = rule.apply(
                first_in=first_in,
                settings=settings,
                day=day,
                work_minutes=work_minutes,
                current=snap,
            )
        return snap
