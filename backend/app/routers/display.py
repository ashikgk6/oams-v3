from fastapi import APIRouter, Depends, HTTPException

from app.application.display_admin_service import DisplayAdminError
from app.application.wallboard_service import WallboardError
from app.container import AppServices, get_services
from app.deps import require_roles
from app.models import User, UserRole
from app.schemas import DisplayTokenCreate, DisplayTokenOut, WallboardOut

router = APIRouter(tags=["display"])


@router.post("/api/display-tokens", response_model=DisplayTokenOut)
def create_display_token(
    body: DisplayTokenCreate,
    admin: User = Depends(require_roles(UserRole.admin)),
    services: AppServices = Depends(get_services),
):
    row, raw = services.display_admin.create_token(admin, body.label)
    return DisplayTokenOut(
        id=row.id,
        label=row.label,
        token=raw,
        token_prefix=row.token_prefix,
        revoked_at=row.revoked_at,
        created_at=row.created_at,
        display_path=f"/display/{raw}",
    )


@router.get("/api/display-tokens", response_model=list[DisplayTokenOut])
def list_display_tokens(
    _: User = Depends(require_roles(UserRole.admin)),
    services: AppServices = Depends(get_services),
):
    return [
        DisplayTokenOut(
            id=r.id,
            label=r.label,
            token=None,
            token_prefix=r.token_prefix,
            revoked_at=r.revoked_at,
            created_at=r.created_at,
            display_path=None,
        )
        for r in services.display_admin.list_tokens()
    ]


@router.post("/api/display-tokens/{token_id}/revoke")
def revoke_display_token(
    token_id: int,
    admin: User = Depends(require_roles(UserRole.admin)),
    services: AppServices = Depends(get_services),
):
    try:
        services.display_admin.revoke(admin, token_id)
    except DisplayAdminError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return {"ok": True}


@router.get("/api/display/{token}", response_model=WallboardOut)
def wallboard_data(token: str, services: AppServices = Depends(get_services)):
    try:
        return services.wallboard.build(token)
    except WallboardError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
