from __future__ import annotations

from app.domain.protocols import Clock, QrTokenService, UnitOfWork
from app.models import Kiosk, User
from app.services.qr import generate_device_secret, generate_pair_code


class KioskError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class KioskApplicationService:
    def __init__(self, uow: UnitOfWork, qr: QrTokenService, clock: Clock) -> None:
        self._uow = uow
        self._qr = qr
        self._clock = clock

    def list_kiosks(self) -> list[Kiosk]:
        return self._uow.kiosks.list_all()

    def create(self, actor: User, name: str) -> Kiosk:
        code = generate_pair_code()
        while self._uow.kiosks.get_by_pair_code(code):
            code = generate_pair_code()
        kiosk = self._uow.kiosks.add(Kiosk(name=name, pair_code=code, active=True))
        self._uow.audit.record(
            "kiosk.create", actor.id, {"id": kiosk.id, "name": kiosk.name}
        )
        self._uow.commit()
        self._uow.refresh(kiosk)
        return kiosk

    def pair(self, pair_code: str) -> tuple[Kiosk, str]:
        kiosk = self._uow.kiosks.get_by_pair_code(pair_code)
        if not kiosk:
            raise KioskError("Invalid pair code", 404)
        secret = generate_device_secret()
        kiosk.secret = secret
        kiosk.paired_at = self._clock.now()
        kiosk.pair_code = None
        self._uow.kiosks.save(kiosk)
        self._uow.audit.record("kiosk.paired", None, {"kiosk_id": kiosk.id})
        self._uow.commit()
        return kiosk, secret

    def qr_payload(self, kiosk_id: int, device_secret: str) -> tuple[str, int, str]:
        kiosk = self._uow.kiosks.get(kiosk_id)
        if not kiosk or not kiosk.active or not kiosk.secret or kiosk.secret != device_secret:
            raise KioskError("Kiosk not authorized", 401)
        token, ttl = self._qr.sign(kiosk.id, kiosk.secret)
        return token, ttl, kiosk.name

    def rotate_pair_code(self, actor: User, kiosk_id: int) -> Kiosk:
        kiosk = self._uow.kiosks.get(kiosk_id)
        if not kiosk:
            raise KioskError("Not found", 404)
        kiosk.pair_code = generate_pair_code()
        kiosk.secret = None
        kiosk.paired_at = None
        self._uow.kiosks.save(kiosk)
        self._uow.audit.record("kiosk.repair", actor.id, {"kiosk_id": kiosk_id})
        self._uow.commit()
        self._uow.refresh(kiosk)
        return kiosk
