from fastapi import APIRouter, Depends, Header, HTTPException

from app.application.kiosk_service import KioskError
from app.container import AppServices, get_services
from app.deps import require_roles
from app.models import User, UserRole
from app.schemas import KioskCreate, KioskOut, KioskPairIn, KioskPairOut, QrPayloadOut

router = APIRouter(prefix="/api/kiosks", tags=["kiosks"])


@router.get("", response_model=list[KioskOut])
def list_kiosks(
    _: User = Depends(require_roles(UserRole.admin)),
    services: AppServices = Depends(get_services),
):
    return services.kiosks.list_kiosks()


@router.post("", response_model=KioskOut)
def create_kiosk(
    body: KioskCreate,
    admin: User = Depends(require_roles(UserRole.admin)),
    services: AppServices = Depends(get_services),
):
    return services.kiosks.create(admin, body.name)


@router.post("/pair", response_model=KioskPairOut)
def pair_kiosk(body: KioskPairIn, services: AppServices = Depends(get_services)):
    try:
        kiosk, secret = services.kiosks.pair(body.pair_code)
    except KioskError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return KioskPairOut(kiosk_id=kiosk.id, name=kiosk.name, device_secret=secret)


@router.get("/{kiosk_id}/qr", response_model=QrPayloadOut)
def get_kiosk_qr(
    kiosk_id: int,
    x_kiosk_secret: str = Header(..., alias="X-Kiosk-Secret"),
    services: AppServices = Depends(get_services),
):
    try:
        token, ttl, name = services.kiosks.qr_payload(kiosk_id, x_kiosk_secret)
    except KioskError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return QrPayloadOut(token=token, expires_in=ttl, kiosk_name=name)


@router.post("/{kiosk_id}/rotate-pair-code", response_model=KioskOut)
def rotate_pair_code(
    kiosk_id: int,
    admin: User = Depends(require_roles(UserRole.admin)),
    services: AppServices = Depends(get_services),
):
    try:
        return services.kiosks.rotate_pair_code(admin, kiosk_id)
    except KioskError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
