from __future__ import annotations

from datetime import date, timedelta

from app.application.attendance_service import AttendanceApplicationService
from app.domain.protocols import Clock, UnitOfWork
from app.models import LeaveRequest, LeaveType, RequestStatus, User


class LeaveError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class LeaveApplicationService:
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
        leave_type: LeaveType,
        start_date: date,
        end_date: date,
        reason: str | None,
    ) -> LeaveRequest:
        if end_date < start_date:
            raise LeaveError("end_date before start_date")
        row = self._uow.leave.add(
            LeaveRequest(
                user_id=user.id,
                leave_type=leave_type,
                start_date=start_date,
                end_date=end_date,
                reason=reason,
                status=RequestStatus.pending,
            )
        )
        self._uow.audit.record(
            "leave.request", user.id, {"id": row.id, "type": leave_type.value}
        )
        self._uow.commit()
        self._uow.refresh(row)
        return row

    def mine(self, user: User) -> list[LeaveRequest]:
        return self._uow.leave.list_for_user(user.id)

    def pending(self, actor: User) -> list[LeaveRequest]:
        return self._uow.leave.list_pending(self._attendance.scoped_active_user_ids(actor))

    def decide(self, actor: User, leave_id: int, approve: bool) -> LeaveRequest:
        row = self._uow.leave.get(leave_id)
        if not row:
            raise LeaveError("Not found")
        if row.status != RequestStatus.pending:
            raise LeaveError("Already decided")

        row.status = RequestStatus.approved if approve else RequestStatus.rejected
        row.approver_id = actor.id
        row.decided_at = self._clock.now()

        if row.status == RequestStatus.approved:
            user = self._uow.users.get_by_id(row.user_id)
            if user:
                day = row.start_date
                while day <= row.end_date:
                    self._attendance.derive_for_user(user, day)
                    day += timedelta(days=1)

        self._uow.audit.record(
            "leave.decide", actor.id, {"id": leave_id, "approve": approve}
        )
        self._uow.commit()
        self._uow.refresh(row)
        return row
