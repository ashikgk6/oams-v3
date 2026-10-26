from __future__ import annotations

from datetime import date

from app.application.attendance_service import AttendanceApplicationService
from app.domain.protocols import Clock, UnitOfWork
from app.models import PunchCorrection, RequestStatus, User


class CorrectionError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class CorrectionApplicationService:
    def __init__(
        self,
        uow: UnitOfWork,
        attendance: AttendanceApplicationService,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._attendance = attendance
        self._clock = clock

    def request(
        self,
        user: User,
        day: date,
        requested_in,
        requested_out,
        reason: str,
    ) -> PunchCorrection:
        if not requested_in and not requested_out:
            raise CorrectionError("Provide requested_in and/or requested_out")
        row = self._uow.corrections.add(
            PunchCorrection(
                user_id=user.id,
                date=day,
                requested_in=requested_in,
                requested_out=requested_out,
                reason=reason,
                status=RequestStatus.pending,
            )
        )
        self._uow.audit.record(
            "correction.request", user.id, {"id": row.id, "date": str(day)}
        )
        self._uow.commit()
        self._uow.refresh(row)
        return row

    def mine(self, user: User) -> list[PunchCorrection]:
        return self._uow.corrections.list_for_user(user.id)

    def pending(self, actor: User) -> list[PunchCorrection]:
        return self._uow.corrections.list_pending(
            self._attendance.scoped_active_user_ids(actor)
        )

    def decide(self, actor: User, correction_id: int, approve: bool) -> PunchCorrection:
        row = self._uow.corrections.get(correction_id)
        if not row:
            raise CorrectionError("Not found")
        if row.status != RequestStatus.pending:
            raise CorrectionError("Already decided")

        row.status = RequestStatus.approved if approve else RequestStatus.rejected
        row.approver_id = actor.id
        row.decided_at = self._clock.now()
        self._uow.audit.record(
            "correction.decide", actor.id, {"id": correction_id, "approve": approve}
        )
        self._uow.commit()

        if row.status == RequestStatus.approved:
            self._attendance.apply_correction(row)

        self._uow.refresh(row)
        return row
