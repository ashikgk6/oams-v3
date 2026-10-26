from fastapi import APIRouter, Depends, HTTPException

from app.application.leave_service import LeaveError
from app.container import AppServices, get_services
from app.deps import get_current_user, require_roles
from app.models import User, UserRole
from app.schemas import DecisionIn, LeaveCreate, LeaveOut

router = APIRouter(prefix="/api/leave", tags=["leave"])


def _leave_out(row) -> LeaveOut:
    return LeaveOut(
        id=row.id,
        user_id=row.user_id,
        user_name=row.user.name if row.user else None,
        leave_type=row.leave_type,
        start_date=row.start_date,
        end_date=row.end_date,
        reason=row.reason,
        status=row.status,
        created_at=row.created_at,
    )


@router.post("", response_model=LeaveOut)
def request_leave(
    body: LeaveCreate,
    user: User = Depends(get_current_user),
    services: AppServices = Depends(get_services),
):
    try:
        row = services.leave.request(
            user, body.leave_type, body.start_date, body.end_date, body.reason
        )
    except LeaveError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
    return _leave_out(row)


@router.get("/mine", response_model=list[LeaveOut])
def my_leave(
    user: User = Depends(get_current_user),
    services: AppServices = Depends(get_services),
):
    return [_leave_out(r) for r in services.leave.mine(user)]


@router.get("/pending", response_model=list[LeaveOut])
def pending_leave(
    user: User = Depends(require_roles(UserRole.admin, UserRole.manager)),
    services: AppServices = Depends(get_services),
):
    return [_leave_out(r) for r in services.leave.pending(user)]


@router.post("/{leave_id}/decide", response_model=LeaveOut)
def decide_leave(
    leave_id: int,
    body: DecisionIn,
    actor: User = Depends(require_roles(UserRole.admin, UserRole.manager)),
    services: AppServices = Depends(get_services),
):
    try:
        row = services.leave.decide(actor, leave_id, body.approve)
    except LeaveError as exc:
        code = 404 if exc.message == "Not found" else 400
        raise HTTPException(status_code=code, detail=exc.message) from exc
    return _leave_out(row)
