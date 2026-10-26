from fastapi import APIRouter, Depends, HTTPException, status

from app.application.identity_service import IdentityError
from app.container import AppServices, get_services
from app.deps import get_current_user
from app.models import User
from app.schemas import LoginIn, TokenOut, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, services: AppServices = Depends(get_services)):
    try:
        user, token = services.identity.login(body.email, body.password)
    except IdentityError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return TokenOut(
        access_token=token,
        role=user.role,
        name=user.name,
        user_id=user.id,
    )


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        team_id=user.team_id,
        team_name=user.team.name if user.team else None,
        active=user.active,
    )
