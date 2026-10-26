from __future__ import annotations

import json
from datetime import date

from sqlalchemy.exc import IntegrityError

from app.application.attendance_service import AttendanceApplicationService
from app.domain.protocols import Clock, UnitOfWork


class JobApplicationService:
    def __init__(
        self,
        uow: UnitOfWork,
        attendance: AttendanceApplicationService,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._attendance = attendance
        self._clock = clock

    def finalize_day(self, day: date | None = None) -> dict:
        target = day or self._clock.today()
        job_key = target.isoformat()
        existing = self._uow.jobs.get("finalize-day", job_key)
        if existing and existing.status == "completed":
            return json.loads(existing.result or "{}")

        try:
            run = self._uow.jobs.start("finalize-day", job_key)
            self._uow.commit()
        except IntegrityError:
            self._uow.rollback()
            existing = self._uow.jobs.get("finalize-day", job_key)
            if existing and existing.status == "completed":
                return json.loads(existing.result or "{}")
            if existing and existing.status == "running":
                return {"date": job_key, "status": "already_running"}
            raise

        try:
            result = self._attendance.finalize_day(target)
            self._uow.jobs.complete(run.id, json.dumps(result), self._clock.now())
            self._uow.commit()
            return result
        except Exception as exc:
            self._uow.jobs.fail(run.id, str(exc), self._clock.now())
            self._uow.commit()
            raise
