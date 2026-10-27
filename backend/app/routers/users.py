from pydantic import BaseModel, ConfigDict

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.application.identity_service import IdentityError
from app.container import AppServices, get_services
from app.deps import get_current_user, require_roles
from app.models import User, UserRole
from app.schemas import TeamCreate, TeamOut, UserCreate, UserOut

router = APIRouter(prefix="/api", tags=["users"])


class TeamUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    manager_id: int | None = None


def _user_out(u: User) -> UserOut:
    return UserOut(
        id=u.id,
        name=u.name,
        email=u.email,
        role=u.role,
        team_id=u.team_id,
        team_name=u.team.name if u.team else None,
        active=u.active,
    )


@router.get("/users", response_model=list[UserOut])
def list_users(
    _: User = Depends(require_roles(UserRole.admin, UserRole.manager)),
    services: AppServices = Depends(get_services),
):
    return [_user_out(u) for u in services.identity.list_users()]


@router.post("/users", response_model=UserOut)
def create_user(
    body: UserCreate,
    admin: User = Depends(require_roles(UserRole.admin)),
    services: AppServices = Depends(get_services),
):
    try:
        user = services.identity.create_user(
            actor=admin,
            name=body.name,
            email=body.email,
            password=body.password,
            role=body.role,
            team_id=body.team_id,
        )
    except IdentityError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return _user_out(user)


@router.post("/users/import-csv")
async def import_users_csv(
    file: UploadFile = File(...),
    admin: User = Depends(require_roles(UserRole.admin)),
    services: AppServices = Depends(get_services),
):
    try:
        raw = (await file.read()).decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="CSV file must be UTF-8 encoded") from exc
    finally:
        await file.close()
    return services.identity.import_csv(admin, raw)


@router.get("/teams", response_model=list[TeamOut])
def list_teams(
    _: User = Depends(get_current_user),
    services: AppServices = Depends(get_services),
):
    return services.identity.list_teams()


@router.post("/teams", response_model=TeamOut)
def create_team(
    body: TeamCreate,
    admin: User = Depends(require_roles(UserRole.admin)),
    services: AppServices = Depends(get_services),
):
    try:
        return services.identity.create_team(admin, body.name, body.manager_id)
    except IdentityError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.patch("/teams/{team_id}", response_model=TeamOut)
def update_team(
    team_id: int,
    body: TeamUpdate,
    admin: User = Depends(require_roles(UserRole.admin)),
    services: AppServices = Depends(get_services),
):
    changes = body.model_dump(exclude_unset=True)
    try:
        return services.identity.update_team(
            admin,
            team_id,
            name=changes.get("name"),
            manager_id=changes.get("manager_id"),
            update_manager="manager_id" in changes,
        )
    except IdentityError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
