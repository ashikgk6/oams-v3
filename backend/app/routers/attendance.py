from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from app.container import AppServices, get_services
from app.deps import get_current_user, require_roles
from app.models import User, UserRole
from app.schemas import AttendanceDayOut, TeamTodayOut

router = APIRouter(prefix="/api/attendance", tags=["attendance"])


@router.get("/me", response_model=list[AttendanceDayOut])
def my_attendance(
    user: User = Depends(get_current_user),
    services: AppServices = Depends(get_services),
    days: int = Query(30, ge=1, le=90),
):
    return services.attendance.my_history(user, days=days)


@router.get("/today")
def office_today(
    user: User = Depends(require_roles(UserRole.admin, UserRole.manager)),
    services: AppServices = Depends(get_services),
):
    return services.attendance.office_today(user)


@router.get("/teams/{team_id}/today", response_model=TeamTodayOut)
def team_today(
    team_id: int,
    user: User = Depends(require_roles(UserRole.admin, UserRole.manager)),
    services: AppServices = Depends(get_services),
):
    team = services.uow.teams.get_by_id(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    if user.role == UserRole.manager and team.manager_id != user.id and user.team_id != team_id:
        raise HTTPException(status_code=403, detail="Not your team")
    d = services.clock.today()
    members = []
    for u in services.uow.users.list_by_team(team_id):
        row = services.attendance.derive_for_user(u, d)
        members.append(
            {
                "user_id": u.id,
                "name": u.name,
                "status": row.status.value,
                "first_in": row.first_in.isoformat() if row.first_in else None,
                "last_out": row.last_out.isoformat() if row.last_out else None,
            }
        )
    services.uow.commit()
    return TeamTodayOut(team_id=team.id, team_name=team.name, members=members)


@router.post("/recompute")
def recompute(
    target_date: date | None = None,
    _: User = Depends(require_roles(UserRole.admin)),
    services: AppServices = Depends(get_services),
):
    return services.attendance.recompute_all(target_date)
