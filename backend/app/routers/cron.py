from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from app.config import get_settings
from app.container import AppServices, get_services

router = APIRouter(prefix="/api/internal", tags=["internal"])
settings = get_settings()


@router.post("/finalize-day")
def finalize(
    target_date: date | None = Query(None),
    x_cron_secret: str = Header(..., alias="X-Cron-Secret"),
    services: AppServices = Depends(get_services),
):
    if x_cron_secret != settings.internal_cron_secret:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return services.jobs.finalize_day(target_date)
