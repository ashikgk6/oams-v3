import csv
import io
from calendar import monthrange
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.container import AppServices, get_services
from app.deps import require_roles
from app.models import AuditLog, User, UserRole
from app.schemas import AuditOut
from app.database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/monthly.csv")
def monthly_csv(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    services: AppServices = Depends(get_services),
    _: User = Depends(require_roles(UserRole.admin, UserRole.manager)),
):
    _, last = monthrange(year, month)
    users = services.uow.users.list_active()
    for day_num in range(1, last + 1):
        day = date(year, month, day_num)
        for user in users:
            services.attendance.derive_for_user(user, day)
    services.uow.commit()

    rows = services.uow.attendance.list_for_month(year, month)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "date",
            "employee",
            "email",
            "team",
            "status",
            "first_in",
            "last_out",
            "work_minutes",
            "late_minutes",
        ]
    )
    for day_row, user in rows:
        writer.writerow(
            [
                day_row.date.isoformat(),
                user.name,
                user.email,
                user.team.name if user.team else "",
                day_row.status.value,
                day_row.first_in.isoformat() if day_row.first_in else "",
                day_row.last_out.isoformat() if day_row.last_out else "",
                day_row.work_minutes if day_row.work_minutes is not None else "",
                day_row.late_minutes if day_row.late_minutes is not None else "",
            ]
        )
    buf.seek(0)
    filename = f"attendance_{year}_{month:02d}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/audit", response_model=list[AuditOut])
def audit_logs(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin)),
):
    return db.query(AuditLog).order_by(AuditLog.id.desc()).limit(limit).all()
