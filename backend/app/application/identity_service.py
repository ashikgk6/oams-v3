from __future__ import annotations

import csv
import io

from app.domain.protocols import UnitOfWork
from app.models import Team, User, UserRole
from app.security import create_access_token, hash_password, verify_password


class IdentityError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class IdentityApplicationService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def login(self, email: str, password: str) -> tuple[User, str]:
        user = self._uow.users.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise IdentityError("Invalid credentials", 401)
        if not user.active:
            raise IdentityError("Account disabled", 401)
        token = create_access_token(user.email, user.role.value)
        return user, token

    def list_users(self) -> list[User]:
        return self._uow.users.list_all()

    def create_user(
        self,
        *,
        actor: User,
        name: str,
        email: str,
        password: str,
        role: UserRole,
        team_id: int | None,
    ) -> User:
        email = email.lower()
        if self._uow.users.get_by_email(email):
            raise IdentityError("Email already exists")
        user = self._uow.users.add(
            User(
                name=name,
                email=email,
                hashed_password=hash_password(password),
                role=role,
                team_id=team_id,
                active=True,
            )
        )
        self._uow.audit.record(
            "user.create", actor.id, {"email": email, "role": role.value}
        )
        self._uow.commit()
        self._uow.refresh(user)
        return user

    def import_csv(self, actor: User, raw_csv: str) -> dict:
        reader = csv.DictReader(io.StringIO(raw_csv))
        created, skipped, errors = [], [], []
        for i, row in enumerate(reader, start=2):
            try:
                name = (row.get("name") or "").strip()
                email = (row.get("email") or "").strip().lower()
                if not name or not email:
                    errors.append({"line": i, "error": "name and email required"})
                    continue
                if self._uow.users.get_by_email(email):
                    skipped.append(email)
                    continue
                role_raw = (row.get("role") or "employee").strip().lower()
                role = (
                    UserRole(role_raw)
                    if role_raw in UserRole.__members__
                    else UserRole.employee
                )
                team_name = (row.get("team") or "").strip()
                team_id = None
                if team_name:
                    team = self._uow.teams.get_by_name(team_name)
                    if not team:
                        team = self._uow.teams.add(Team(name=team_name))
                    team_id = team.id
                password = (row.get("password") or "Welcome@123").strip() or "Welcome@123"
                self._uow.users.add(
                    User(
                        name=name,
                        email=email,
                        hashed_password=hash_password(password),
                        role=role,
                        team_id=team_id,
                        active=True,
                    )
                )
                created.append(email)
            except Exception as exc:  # noqa: BLE001
                errors.append({"line": i, "error": str(exc)})
        self._uow.audit.record(
            "user.import_csv",
            actor.id,
            {"created": len(created), "skipped": len(skipped), "errors": len(errors)},
        )
        self._uow.commit()
        return {"created": created, "skipped": skipped, "errors": errors}

    def list_teams(self) -> list[Team]:
        return self._uow.teams.list_all()

    def create_team(self, actor: User, name: str, manager_id: int | None) -> Team:
        if self._uow.teams.get_by_name(name):
            raise IdentityError("Team exists")
        team = self._uow.teams.add(Team(name=name, manager_id=manager_id))
        self._uow.audit.record("team.create", actor.id, {"name": name})
        self._uow.commit()
        self._uow.refresh(team)
        return team
