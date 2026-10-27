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
        name = name.strip()
        email = email.strip().lower()
        if not name:
            raise IdentityError("Name is required")
        if not email:
            raise IdentityError("Email is required")
        if not password:
            raise IdentityError("Password is required")
        if self._uow.users.get_by_email(email):
            raise IdentityError("Email already exists")
        if team_id is not None and not any(
            team.id == team_id for team in self._uow.teams.list_all()
        ):
            raise IdentityError("Team not found", 404)

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
        """Import users from CSV without assigning a shared default password."""
        reader = csv.DictReader(io.StringIO(raw_csv))
        required_columns = {"name", "email", "password"}
        headers = {header.strip().lower() for header in (reader.fieldnames or []) if header}
        if not required_columns.issubset(headers):
            missing = ", ".join(sorted(required_columns - headers))
            return {
                "created": [],
                "skipped": [],
                "errors": [{"line": 1, "error": f"Missing required CSV column(s): {missing}"}],
            }

        created, skipped, errors = [], [], []
        for i, row in enumerate(reader, start=2):
            try:
                # Normalize header names, while preserving the CSV row's values.
                normalized_row = {
                    (key or "").strip().lower(): value
                    for key, value in row.items()
                    if key is not None
                }
                name = (normalized_row.get("name") or "").strip()
                email = (normalized_row.get("email") or "").strip().lower()
                password = (normalized_row.get("password") or "").strip()

                if not name or not email:
                    errors.append({"line": i, "error": "name and email are required"})
                    continue
                if not password:
                    errors.append({"line": i, "error": "password is required"})
                    continue
                if self._uow.users.get_by_email(email):
                    skipped.append(email)
                    continue

                role_raw = (normalized_row.get("role") or "employee").strip().lower()
                try:
                    role = UserRole(role_raw)
                except ValueError:
                    errors.append({
                        "line": i,
                        "error": "role must be employee, manager, or admin",
                    })
                    continue

                team_name = (normalized_row.get("team") or "").strip()
                team_id = None
                if team_name:
                    team = self._uow.teams.get_by_name(team_name)
                    if not team:
                        team = self._uow.teams.add(Team(name=team_name))
                    team_id = team.id

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

    def _validate_manager(self, manager_id: int | None) -> User | None:
        if manager_id is None:
            return None
        manager = next(
            (user for user in self._uow.users.list_all() if user.id == manager_id),
            None,
        )
        if manager is None:
            raise IdentityError("Manager user not found", 404)
        if manager.role != UserRole.manager:
            raise IdentityError("Assigned user must have the manager role")
        if not manager.active:
            raise IdentityError("Cannot assign an inactive manager")
        return manager

    def create_team(self, actor: User, name: str, manager_id: int | None) -> Team:
        name = name.strip()
        if not name:
            raise IdentityError("Team name is required")
        if self._uow.teams.get_by_name(name):
            raise IdentityError("Team exists")
        self._validate_manager(manager_id)
        team = self._uow.teams.add(Team(name=name, manager_id=manager_id))
        self._uow.audit.record(
            "team.create", actor.id, {"name": name, "manager_id": manager_id}
        )
        self._uow.commit()
        self._uow.refresh(team)
        return team

    def update_team(
        self,
        actor: User,
        team_id: int,
        *,
        name: str | None = None,
        manager_id: int | None = None,
        update_manager: bool = False,
    ) -> Team:
        team = next(
            (item for item in self._uow.teams.list_all() if item.id == team_id),
            None,
        )
        if team is None:
            raise IdentityError("Team not found", 404)

        changes: dict[str, object] = {}
        if name is not None:
            name = name.strip()
            if not name:
                raise IdentityError("Team name is required")
            existing = self._uow.teams.get_by_name(name)
            if existing and existing.id != team.id:
                raise IdentityError("Team exists")
            team.name = name
            changes["name"] = name

        if update_manager:
            self._validate_manager(manager_id)
            team.manager_id = manager_id
            changes["manager_id"] = manager_id

        if not changes:
            raise IdentityError("No team changes supplied")

        self._uow.audit.record("team.update", actor.id, {"team_id": team_id, **changes})
        self._uow.commit()
        self._uow.refresh(team)
        return team
