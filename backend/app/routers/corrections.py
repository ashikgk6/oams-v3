from fastapi import APIRouter, Depends, HTTPException

from app.application.correction_service import CorrectionError
from app.container import AppServices, get_services
from app.deps import get_current_user, require_roles
from app.models import User, UserRole
from app.schemas import CorrectionCreate, CorrectionOut, DecisionIn

router = APIRouter(prefix="/api/corrections", tags=["corrections"])


def _out(row) -> CorrectionOut:
    return CorrectionOut(
        id=row.id,
        user_id=row.user_id,
        user_name=row.user.name if row.user else None,
        date=row.date,
        requested_in=row.requested_in,
        requested_out=row.requested_out,
        reason=row.reason,
        status=row.status,
        created_at=row.created_at,
    )


@router.post("", response_model=CorrectionOut)
def request_correction(
    body: CorrectionCreate,
    user: User = Depends(get_current_user),
    services: AppServices = Depends(get_services),
):
    try:
        row = services.corrections.request(
            user, body.date, body.requested_in, body.requested_out, body.reason
        )
    except CorrectionError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
    return _out(row)


@router.get("/mine", response_model=list[CorrectionOut])
def my_corrections(
    user: User = Depends(get_current_user),
    services: AppServices = Depends(get_services),
):
    return [_out(r) for r in services.corrections.mine(user)]


@router.get("/pending", response_model=list[CorrectionOut])
def pending_corrections(
    user: User = Depends(require_roles(UserRole.admin, UserRole.manager)),
    services: AppServices = Depends(get_services),
):
    return [_out(r) for r in services.corrections.pending(user)]


@router.post("/{correction_id}/decide", response_model=CorrectionOut)
def decide_correction(
    correction_id: int,
    body: DecisionIn,
    actor: User = Depends(require_roles(UserRole.admin, UserRole.manager)),
    services: AppServices = Depends(get_services),
):
    try:
        row = services.corrections.decide(actor, correction_id, body.approve)
    except CorrectionError as exc:
        code = 404 if exc.message == "Not found" else 400
        raise HTTPException(status_code=code, detail=exc.message) from exc
    return _out(row)
