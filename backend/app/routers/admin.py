from fastapi import APIRouter, Depends, HTTPException

from app.application.admin_service import AdminError
from app.container import AppServices, get_services
from app.deps import require_roles
from app.models import User, UserRole
from app.schemas import HolidayCreate, HolidayOut, OfficeSettingsOut, OfficeSettingsUpdate

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/settings", response_model=OfficeSettingsOut)
def get_settings_route(
    _: User = Depends(require_roles(UserRole.admin, UserRole.manager)),
    services: AppServices = Depends(get_services),
):
    return services.admin.get_settings()


@router.patch("/settings", response_model=OfficeSettingsOut)
def update_settings(
    body: OfficeSettingsUpdate,
    admin: User = Depends(require_roles(UserRole.admin)),
    services: AppServices = Depends(get_services),
):
    return services.admin.update_settings(admin, body.model_dump(exclude_unset=True))


@router.get("/holidays", response_model=list[HolidayOut])
def list_holidays(
    _: User = Depends(require_roles(UserRole.admin, UserRole.manager)),
    services: AppServices = Depends(get_services),
):
    return services.admin.list_holidays()


@router.post("/holidays", response_model=HolidayOut)
def add_holiday(
    body: HolidayCreate,
    admin: User = Depends(require_roles(UserRole.admin)),
    services: AppServices = Depends(get_services),
):
    try:
        return services.admin.add_holiday(admin, body.date, body.name)
    except AdminError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.delete("/holidays/{holiday_id}")
def delete_holiday(
    holiday_id: int,
    admin: User = Depends(require_roles(UserRole.admin)),
    services: AppServices = Depends(get_services),
):
    try:
        services.admin.delete_holiday(admin, holiday_id)
    except AdminError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return {"ok": True}
