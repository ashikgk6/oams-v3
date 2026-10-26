from __future__ import annotations

from app.domain.protocols import Clock, UnitOfWork
from app.models import DisplayToken, User
from app.services.qr import generate_display_token, hash_token


class DisplayAdminError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class DisplayAdminApplicationService:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    def create_token(self, actor: User, label: str) -> tuple[DisplayToken, str]:
        raw = generate_display_token()
        row = self._uow.display_tokens.create(
            DisplayToken(
                label=label,
                token_hash=hash_token(raw),
                token_prefix=raw[:8],
            )
        )
        self._uow.audit.record(
            "display_token.create", actor.id, {"id": row.id, "label": label}
        )
        self._uow.commit()
        self._uow.refresh(row)
        return row, raw

    def list_tokens(self) -> list[DisplayToken]:
        return self._uow.display_tokens.list_all()

    def revoke(self, actor: User, token_id: int) -> None:
        if not self._uow.display_tokens.revoke(token_id, self._clock.now()):
            raise DisplayAdminError("Not found", 404)
        self._uow.audit.record("display_token.revoke", actor.id, {"id": token_id})
        self._uow.commit()
