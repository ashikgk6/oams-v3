import enum
from datetime import date, datetime, time
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, enum.Enum):
    employee = "employee"
    manager = "manager"
    admin = "admin"


class PunchDirection(str, enum.Enum):
    IN = "IN"
    OUT = "OUT"


class AttendanceStatus(str, enum.Enum):
    present = "present"
    late = "late"
    absent = "absent"
    on_leave = "on_leave"
    half_day = "half_day"
    holiday = "holiday"
    weekend = "weekend"


class LeaveType(str, enum.Enum):
    CL = "CL"
    SL = "SL"
    EL = "EL"
    OTHER = "OTHER"


class RequestStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


def _enum(enum_cls):
    """Store enums as varchar so SQLite and Postgres stay compatible."""
    return Enum(
        enum_cls,
        values_callable=lambda obj: [e.value for e in obj],
        native_enum=False,
        length=32,
    )


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    manager_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)

    members: Mapped[list["User"]] = relationship(
        "User", back_populates="team", foreign_keys="User.team_id"
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(_enum(UserRole), default=UserRole.employee, nullable=False)
    team_id: Mapped[Optional[int]] = mapped_column(ForeignKey("teams.id"), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    team: Mapped[Optional[Team]] = relationship(
        "Team", back_populates="members", foreign_keys=[team_id]
    )


class Kiosk(Base):
    __tablename__ = "kiosks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    pair_code: Mapped[Optional[str]] = mapped_column(String(16), unique=True, nullable=True)
    secret: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    paired_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DisplayToken(Base):
    __tablename__ = "display_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    token_prefix: Mapped[str] = mapped_column(String(12), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PunchEvent(Base):
    __tablename__ = "punch_events"
    __table_args__ = (
        Index("ix_punch_user_ts", "user_id", "ts"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    direction: Mapped[PunchDirection] = mapped_column(_enum(PunchDirection), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    kiosk_id: Mapped[Optional[int]] = mapped_column(ForeignKey("kiosks.id"), nullable=True)
    source: Mapped[str] = mapped_column(String(40), default="qr", nullable=False)
    nonce: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(128), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship("User")


class AttendanceDay(Base):
    __tablename__ = "attendance_days"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_attendance_user_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[AttendanceStatus] = mapped_column(_enum(AttendanceStatus), nullable=False)
    first_in: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_out: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    work_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    late_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    finalized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    user: Mapped[User] = relationship("User")


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    leave_type: Mapped[LeaveType] = mapped_column(_enum(LeaveType), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[RequestStatus] = mapped_column(
        _enum(RequestStatus), default=RequestStatus.pending, nullable=False
    )
    approver_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship("User", foreign_keys=[user_id])


class PunchCorrection(Base):
    __tablename__ = "punch_corrections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    requested_in: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    requested_out: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[RequestStatus] = mapped_column(
        _enum(RequestStatus), default=RequestStatus.pending, nullable=False
    )
    approver_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship("User", foreign_keys=[user_id])


class Holiday(Base):
    __tablename__ = "holidays"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)


class OfficeSettings(Base):
    __tablename__ = "office_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    office_name: Mapped[str] = mapped_column(String(200), default="OAMS Office")
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata")
    shift_start: Mapped[time] = mapped_column(Time, nullable=False)
    shift_end: Mapped[time] = mapped_column(Time, nullable=False)
    grace_minutes: Mapped[int] = mapped_column(Integer, default=15)
    half_day_after: Mapped[time] = mapped_column(Time, nullable=False)
    min_half_day_minutes: Mapped[int] = mapped_column(Integer, default=240)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UsedNonce(Base):
    __tablename__ = "used_nonces"

    nonce: Mapped[str] = mapped_column(String(64), primary_key=True)
    used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class JobRun(Base):
    """Idempotent background job ledger (e.g. finalize-day)."""

    __tablename__ = "job_runs"
    __table_args__ = (UniqueConstraint("job_name", "job_key", name="uq_job_name_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_name: Mapped[str] = mapped_column(String(80), nullable=False)
    job_key: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
