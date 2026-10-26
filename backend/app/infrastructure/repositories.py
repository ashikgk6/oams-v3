from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from typing import Optional, Sequence

from sqlalchemy.orm import Session

from app.domain.clock import IST
from app.models import (
    AttendanceDay,
    AuditLog,
    DisplayToken,
    Holiday,
    JobRun,
    Kiosk,
    LeaveRequest,
    OfficeSettings,
    PunchCorrection,
    PunchDirection,
    PunchEvent,
    RequestStatus,
    Team,
    UsedNonce,
    User,
)
from app.services.qr import hash_token


def _day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime(day.year, day.month, day.day, tzinfo=IST)
    return start, start + timedelta(days=1)


class SqlUserRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self._db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self._db.query(User).filter(User.email == email.lower()).first()

    def list_active(self, *, team_ids: Optional[Sequence[int]] = None) -> list[User]:
        q = self._db.query(User).filter(User.active.is_(True))
        if team_ids is not None:
            q = q.filter(User.team_id.in_(list(team_ids) or [-1]))
        return q.order_by(User.name).all()

    def list_by_team(self, team_id: int) -> list[User]:
        return (
            self._db.query(User)
            .filter(User.team_id == team_id, User.active.is_(True))
            .order_by(User.name)
            .all()
        )

    def add(self, user: User) -> User:
        self._db.add(user)
        self._db.flush()
        return user

    def list_all(self) -> list[User]:
        return self._db.query(User).order_by(User.name).all()


class SqlTeamRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, team_id: int) -> Optional[Team]:
        return self._db.query(Team).filter(Team.id == team_id).first()

    def get_by_name(self, name: str) -> Optional[Team]:
        return self._db.query(Team).filter(Team.name == name).first()

    def list_all(self) -> list[Team]:
        return self._db.query(Team).order_by(Team.name).all()

    def list_managed_by(self, manager_id: int) -> list[Team]:
        return self._db.query(Team).filter(Team.manager_id == manager_id).all()

    def add(self, team: Team) -> Team:
        self._db.add(team)
        self._db.flush()
        return team


class SqlPunchRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_for_user_day(self, user_id: int, day: date) -> list[PunchEvent]:
        start, end = _day_bounds(day)
        return (
            self._db.query(PunchEvent)
            .filter(
                PunchEvent.user_id == user_id,
                PunchEvent.ts >= start,
                PunchEvent.ts < end,
            )
            .order_by(PunchEvent.ts.asc())
            .all()
        )

    def last_for_user_day(self, user_id: int, day: date) -> Optional[PunchEvent]:
        start, end = _day_bounds(day)
        return (
            self._db.query(PunchEvent)
            .filter(
                PunchEvent.user_id == user_id,
                PunchEvent.ts >= start,
                PunchEvent.ts < end,
            )
            .order_by(PunchEvent.ts.desc())
            .first()
        )

    def find_recent(
        self, user_id: int, direction: PunchDirection, since: datetime
    ) -> Optional[PunchEvent]:
        return (
            self._db.query(PunchEvent)
            .filter(
                PunchEvent.user_id == user_id,
                PunchEvent.direction == direction,
                PunchEvent.ts >= since,
            )
            .first()
        )

    def get_by_idempotency_key(self, key: str) -> Optional[PunchEvent]:
        return (
            self._db.query(PunchEvent)
            .filter(PunchEvent.idempotency_key == key)
            .first()
        )

    def add(self, event: PunchEvent) -> PunchEvent:
        self._db.add(event)
        self._db.flush()
        return event

    def delete_for_user_day(self, user_id: int, day: date) -> None:
        start, end = _day_bounds(day)
        self._db.query(PunchEvent).filter(
            PunchEvent.user_id == user_id,
            PunchEvent.ts >= start,
            PunchEvent.ts < end,
        ).delete(synchronize_session=False)

    def list_for_user(self, user_id: int, limit: int = 50) -> list[PunchEvent]:
        return (
            self._db.query(PunchEvent)
            .filter(PunchEvent.user_id == user_id)
            .order_by(PunchEvent.ts.desc())
            .limit(limit)
            .all()
        )


class SqlAttendanceRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(
        self, user_id: int, day: date, *, for_update: bool = False
    ) -> Optional[AttendanceDay]:
        q = self._db.query(AttendanceDay).filter(
            AttendanceDay.user_id == user_id, AttendanceDay.date == day
        )
        if for_update and self._db.bind and self._db.bind.dialect.name != "sqlite":
            q = q.with_for_update()
        return q.first()

    def upsert(self, row: AttendanceDay) -> AttendanceDay:
        if row.id is not None:
            row.version = (row.version or 1) + 1
        self._db.add(row)
        self._db.flush()
        return row

    def list_for_user_range(self, user_id: int, start: date, end: date) -> list[AttendanceDay]:
        return (
            self._db.query(AttendanceDay)
            .filter(
                AttendanceDay.user_id == user_id,
                AttendanceDay.date >= start,
                AttendanceDay.date <= end,
            )
            .order_by(AttendanceDay.date.desc())
            .all()
        )

    def list_for_date(self, day: date) -> list[AttendanceDay]:
        return (
            self._db.query(AttendanceDay)
            .filter(AttendanceDay.date == day)
            .all()
        )

    def list_for_month(self, year: int, month: int) -> list[tuple[AttendanceDay, User]]:
        from calendar import monthrange

        _, last = monthrange(year, month)
        return (
            self._db.query(AttendanceDay, User)
            .join(User, User.id == AttendanceDay.user_id)
            .filter(
                AttendanceDay.date >= date(year, month, 1),
                AttendanceDay.date <= date(year, month, last),
                User.active.is_(True),
            )
            .order_by(User.name, AttendanceDay.date)
            .all()
        )


class SqlLeaveRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def approved_on(self, user_id: int, day: date) -> Optional[LeaveRequest]:
        return (
            self._db.query(LeaveRequest)
            .filter(
                LeaveRequest.user_id == user_id,
                LeaveRequest.status == RequestStatus.approved,
                LeaveRequest.start_date <= day,
                LeaveRequest.end_date >= day,
            )
            .first()
        )

    def add(self, row: LeaveRequest) -> LeaveRequest:
        self._db.add(row)
        self._db.flush()
        return row

    def get(self, leave_id: int) -> Optional[LeaveRequest]:
        return self._db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()

    def list_for_user(self, user_id: int) -> list[LeaveRequest]:
        return (
            self._db.query(LeaveRequest)
            .filter(LeaveRequest.user_id == user_id)
            .order_by(LeaveRequest.created_at.desc())
            .all()
        )

    def list_pending(self, user_ids: Optional[Sequence[int]] = None) -> list[LeaveRequest]:
        q = self._db.query(LeaveRequest).filter(LeaveRequest.status == RequestStatus.pending)
        if user_ids is not None:
            q = q.filter(LeaveRequest.user_id.in_(list(user_ids) or [-1]))
        return q.order_by(LeaveRequest.created_at.asc()).all()


class SqlCorrectionRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, row: PunchCorrection) -> PunchCorrection:
        self._db.add(row)
        self._db.flush()
        return row

    def get(self, correction_id: int) -> Optional[PunchCorrection]:
        return self._db.query(PunchCorrection).filter(PunchCorrection.id == correction_id).first()

    def list_for_user(self, user_id: int) -> list[PunchCorrection]:
        return (
            self._db.query(PunchCorrection)
            .filter(PunchCorrection.user_id == user_id)
            .order_by(PunchCorrection.created_at.desc())
            .all()
        )

    def list_pending(self, user_ids: Optional[Sequence[int]] = None) -> list[PunchCorrection]:
        q = self._db.query(PunchCorrection).filter(PunchCorrection.status == RequestStatus.pending)
        if user_ids is not None:
            q = q.filter(PunchCorrection.user_id.in_(list(user_ids) or [-1]))
        return q.order_by(PunchCorrection.created_at.asc()).all()


class SqlKioskRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, kiosk_id: int) -> Optional[Kiosk]:
        return self._db.query(Kiosk).filter(Kiosk.id == kiosk_id).first()

    def get_active_secret(self, kiosk_id: int) -> Optional[str]:
        kiosk = (
            self._db.query(Kiosk)
            .filter(Kiosk.id == kiosk_id, Kiosk.active.is_(True))
            .first()
        )
        return kiosk.secret if kiosk else None

    def get_by_pair_code(self, code: str) -> Optional[Kiosk]:
        return (
            self._db.query(Kiosk)
            .filter(Kiosk.pair_code == code.upper().strip(), Kiosk.active.is_(True))
            .first()
        )

    def list_all(self) -> list[Kiosk]:
        return self._db.query(Kiosk).order_by(Kiosk.id).all()

    def add(self, kiosk: Kiosk) -> Kiosk:
        self._db.add(kiosk)
        self._db.flush()
        return kiosk

    def save(self, kiosk: Kiosk) -> Kiosk:
        self._db.add(kiosk)
        self._db.flush()
        return kiosk


class SqlSettingsRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_or_create(self) -> OfficeSettings:
        settings = self._db.query(OfficeSettings).first()
        if settings:
            return settings
        settings = OfficeSettings(
            office_name="OAMS Office",
            timezone="Asia/Kolkata",
            shift_start=time(9, 30),
            shift_end=time(18, 30),
            grace_minutes=15,
            half_day_after=time(13, 30),
            min_half_day_minutes=240,
        )
        self._db.add(settings)
        self._db.flush()
        return settings

    def save(self, settings: OfficeSettings) -> OfficeSettings:
        self._db.add(settings)
        self._db.flush()
        return settings

    def is_holiday(self, day: date) -> Optional[Holiday]:
        return self._db.query(Holiday).filter(Holiday.date == day).first()

    def list_holidays(self) -> list[Holiday]:
        return self._db.query(Holiday).order_by(Holiday.date).all()

    def add_holiday(self, holiday: Holiday) -> Holiday:
        self._db.add(holiday)
        self._db.flush()
        return holiday

    def delete_holiday(self, holiday_id: int) -> bool:
        row = self._db.query(Holiday).filter(Holiday.id == holiday_id).first()
        if not row:
            return False
        self._db.delete(row)
        return True


class SqlNonceRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def exists(self, nonce: str) -> bool:
        return self._db.query(UsedNonce).filter(UsedNonce.nonce == nonce).first() is not None

    def mark_used(self, nonce: str) -> None:
        self._db.add(UsedNonce(nonce=nonce))
        self._db.flush()


class SqlDisplayTokenRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def resolve_active(self, raw_token: str) -> bool:
        return (
            self._db.query(DisplayToken)
            .filter(
                DisplayToken.token_hash == hash_token(raw_token),
                DisplayToken.revoked_at.is_(None),
            )
            .first()
            is not None
        )

    def create(self, row: DisplayToken) -> DisplayToken:
        self._db.add(row)
        self._db.flush()
        return row

    def list_all(self) -> list[DisplayToken]:
        return self._db.query(DisplayToken).order_by(DisplayToken.id.desc()).all()

    def revoke(self, token_id: int, when: datetime) -> bool:
        row = self._db.query(DisplayToken).filter(DisplayToken.id == token_id).first()
        if not row:
            return False
        row.revoked_at = when
        return True


class SqlJobRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, job_name: str, job_key: str) -> Optional[JobRun]:
        return (
            self._db.query(JobRun)
            .filter(JobRun.job_name == job_name, JobRun.job_key == job_key)
            .first()
        )

    def start(self, job_name: str, job_key: str) -> JobRun:
        run = JobRun(job_name=job_name, job_key=job_key, status="running")
        self._db.add(run)
        self._db.flush()
        return run

    def complete(self, run_id: int, result: str, when: datetime) -> None:
        run = self._db.query(JobRun).filter(JobRun.id == run_id).one()
        run.status = "completed"
        run.result = result
        run.finished_at = when

    def fail(self, run_id: int, result: str, when: datetime) -> None:
        run = self._db.query(JobRun).filter(JobRun.id == run_id).one()
        run.status = "failed"
        run.result = result
        run.finished_at = when


class SqlAuditAdapter:
    def __init__(self, db: Session) -> None:
        self._db = db

    def record(
        self, action: str, actor_id: Optional[int] = None, payload: Optional[dict] = None
    ) -> None:
        self._db.add(
            AuditLog(
                actor_id=actor_id,
                action=action,
                payload=json.dumps(payload) if payload is not None else None,
            )
        )
        self._db.flush()


class SqlUnitOfWork:
    def __init__(self, db: Session) -> None:
        self._db = db
        self.users = SqlUserRepository(db)
        self.teams = SqlTeamRepository(db)
        self.punches = SqlPunchRepository(db)
        self.attendance = SqlAttendanceRepository(db)
        self.leave = SqlLeaveRepository(db)
        self.corrections = SqlCorrectionRepository(db)
        self.kiosks = SqlKioskRepository(db)
        self.settings = SqlSettingsRepository(db)
        self.nonces = SqlNonceRepository(db)
        self.display_tokens = SqlDisplayTokenRepository(db)
        self.jobs = SqlJobRepository(db)
        self.audit = SqlAuditAdapter(db)

    def commit(self) -> None:
        self._db.commit()

    def refresh(self, obj: object) -> None:
        self._db.refresh(obj)

    def rollback(self) -> None:
        self._db.rollback()
