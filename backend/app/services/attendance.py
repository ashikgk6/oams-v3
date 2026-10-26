"""Compatibility shim — attendance logic lives in application services."""

from app.application.attendance_service import AttendanceApplicationService
from app.domain.attendance.policy import DefaultAttendancePolicy, WorkMinutesCalculator
from app.domain.clock import IstClock
from app.infrastructure.repositories import SqlUnitOfWork

__all__ = [
    "AttendanceApplicationService",
    "DefaultAttendancePolicy",
    "WorkMinutesCalculator",
    "IstClock",
    "SqlUnitOfWork",
]
