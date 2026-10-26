"""FastAPI dependency wiring for one request-scoped service graph."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends
from sqlalchemy.orm import Session

from app.application.admin_service import AdminApplicationService
from app.application.attendance_service import AttendanceApplicationService
from app.application.correction_service import CorrectionApplicationService
from app.application.display_admin_service import DisplayAdminApplicationService
from app.application.identity_service import IdentityApplicationService
from app.application.job_service import JobApplicationService
from app.application.kiosk_service import KioskApplicationService
from app.application.leave_service import LeaveApplicationService
from app.application.punch_service import PunchApplicationService
from app.application.wallboard_service import WallboardApplicationService
from app.config import Settings, get_settings
from app.database import get_db
from app.domain.attendance.policy import DefaultAttendancePolicy
from app.domain.clock import IstClock
from app.domain.protocols import AttendancePolicy, Clock, QrTokenService, UnitOfWork
from app.infrastructure.qr_tokens import HmacQrTokenService
from app.infrastructure.repositories import SqlUnitOfWork


@dataclass
class AppServices:
    uow: UnitOfWork
    clock: Clock
    policy: AttendancePolicy
    qr: QrTokenService
    attendance: AttendanceApplicationService
    punches: PunchApplicationService
    leave: LeaveApplicationService
    corrections: CorrectionApplicationService
    wallboard: WallboardApplicationService
    identity: IdentityApplicationService
    admin: AdminApplicationService
    kiosks: KioskApplicationService
    display_admin: DisplayAdminApplicationService
    jobs: JobApplicationService
    settings: Settings


def get_uow(db: Session = Depends(get_db)) -> UnitOfWork:
    return SqlUnitOfWork(db)


def get_clock() -> Clock:
    return IstClock()


def get_policy() -> AttendancePolicy:
    return DefaultAttendancePolicy()


def get_qr_service() -> QrTokenService:
    return HmacQrTokenService()


def get_services(
    uow: UnitOfWork = Depends(get_uow),
    clock: Clock = Depends(get_clock),
    policy: AttendancePolicy = Depends(get_policy),
    qr: QrTokenService = Depends(get_qr_service),
    settings: Settings = Depends(get_settings),
) -> AppServices:
    attendance = AttendanceApplicationService(uow=uow, policy=policy, clock=clock)
    return AppServices(
        uow=uow,
        clock=clock,
        policy=policy,
        qr=qr,
        attendance=attendance,
        punches=PunchApplicationService(
            uow=uow, attendance=attendance, qr=qr, clock=clock, settings=settings
        ),
        leave=LeaveApplicationService(uow=uow, attendance=attendance, clock=clock),
        corrections=CorrectionApplicationService(
            uow=uow, attendance=attendance, clock=clock
        ),
        wallboard=WallboardApplicationService(uow=uow, clock=clock),
        identity=IdentityApplicationService(uow=uow),
        admin=AdminApplicationService(uow=uow),
        kiosks=KioskApplicationService(uow=uow, qr=qr, clock=clock),
        display_admin=DisplayAdminApplicationService(uow=uow, clock=clock),
        jobs=JobApplicationService(uow=uow, attendance=attendance, clock=clock),
        settings=settings,
    )
