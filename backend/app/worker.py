#!/usr/bin/env python3
"""Background finalize-day worker. Run via cron or as a long-lived loop."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from app.application.attendance_service import AttendanceApplicationService
from app.application.job_service import JobApplicationService
from app.database import SessionLocal
from app.domain.attendance.policy import DefaultAttendancePolicy
from app.domain.clock import IstClock
from app.infrastructure.repositories import SqlUnitOfWork


def run_finalize(target: date | None) -> dict:
    db = SessionLocal()
    try:
        uow = SqlUnitOfWork(db)
        clock = IstClock()
        attendance = AttendanceApplicationService(
            uow=uow, policy=DefaultAttendancePolicy(), clock=clock
        )
        jobs = JobApplicationService(uow=uow, attendance=attendance, clock=clock)
        return jobs.finalize_day(target)
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="OAMS finalize-day worker")
    parser.add_argument("--date", help="YYYY-MM-DD (default: today IST)")
    args = parser.parse_args()
    target = date.fromisoformat(args.date) if args.date else None
    result = run_finalize(target)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
