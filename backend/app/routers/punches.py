from fastapi import APIRouter, Depends, Header, HTTPException

from app.application.punch_service import PunchError
from app.container import AppServices, get_services
from app.deps import get_current_user
from app.models import User
from app.schemas import PunchIn, PunchOut

router = APIRouter(prefix="/api/punches", tags=["punches"])


@router.post("", response_model=PunchOut)
def create_punch(
    body: PunchIn,
    user: User = Depends(get_current_user),
    services: AppServices = Depends(get_services),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    try:
        event = services.punches.punch(
            user,
            body.qr_token,
            latitude=body.latitude,
            longitude=body.longitude,
            accuracy_meters=body.accuracy_meters,
            idempotency_key=idempotency_key,
        )
    except PunchError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
    return PunchOut(
        id=event.id,
        direction=event.direction,
        ts=event.ts,
        message=f"{event.direction.value} recorded for {user.name}",
    )


@router.get("/mine")
def my_punches(
    user: User = Depends(get_current_user),
    services: AppServices = Depends(get_services),
    limit: int = 50,
):
    rows = services.punches.list_mine(user, limit=limit)
    return [
        {
            "id": r.id,
            "direction": r.direction.value,
            "ts": r.ts.isoformat(),
            "source": r.source,
        }
        for r in rows
    ]
