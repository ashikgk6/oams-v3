from __future__ import annotations

from datetime import timedelta
from math import asin, cos, radians, sin, sqrt

from app.application.attendance_service import AttendanceApplicationService
from app.config import Settings, get_settings
from app.domain.protocols import Clock, QrTokenService, UnitOfWork
from app.models import PunchEvent, User


class PunchError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class PunchApplicationService:
    def __init__(
        self,
        uow: UnitOfWork,
        attendance: AttendanceApplicationService,
        qr: QrTokenService,
        clock: Clock,
        settings: Settings | None = None,
    ) -> None:
        self._uow = uow
        self._attendance = attendance
        self._qr = qr
        self._clock = clock
        self._settings = settings or get_settings()

    def punch(
        self,
        user: User,
        qr_token: str,
        *,
        latitude: float,
        longitude: float,
        accuracy_meters: float,
        idempotency_key: str | None = None,
    ) -> PunchEvent:
        if accuracy_meters > self._settings.max_location_accuracy_meters:
            raise PunchError(
                "Location accuracy is too low. Enable precise location and try again."
            )

        # Haversine distance between the reported phone location and office.
        earth_radius_m = 6_371_000
        lat1 = radians(self._settings.office_latitude)
        lat2 = radians(latitude)
        delta_lat = radians(latitude - self._settings.office_latitude)
        delta_lon = radians(longitude - self._settings.office_longitude)
        a = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
        distance_m = 2 * earth_radius_m * asin(sqrt(min(1.0, a)))
        if distance_m > self._settings.office_geofence_radius_meters:
            raise PunchError(
                f"You must be within {int(self._settings.office_geofence_radius_meters)} metres of the office. "
                f"Your reported distance is about {round(distance_m)} metres."
            )

        if idempotency_key:
            existing = self._uow.punches.get_by_idempotency_key(idempotency_key)
            if existing:
                return existing

        try:
            payload = self._qr.verify(
                qr_token, lambda kid: self._uow.kiosks.get_active_secret(kid)
            )
        except ValueError as exc:
            raise PunchError(str(exc)) from exc

        nonce = payload["nonce"]
        if self._uow.nonces.exists(nonce):
            raise PunchError("QR already used — wait for next code")

        now = self._clock.now()
        day = self._clock.today()
        direction = self._attendance.next_direction(user.id, day)
        kiosk_id = int(payload["kid"])

        cutoff = now - timedelta(minutes=self._settings.duplicate_punch_minutes)
        if self._uow.punches.find_recent(user.id, direction, cutoff):
            raise PunchError(
                f"Duplicate {direction.value} ignored — already punched recently"
            )

        self._uow.nonces.mark_used(nonce)
        event = self._uow.punches.add(
            PunchEvent(
                user_id=user.id,
                direction=direction,
                ts=now,
                kiosk_id=kiosk_id,
                source="qr",
                nonce=nonce,
                idempotency_key=idempotency_key,
            )
        )
        self._attendance.derive_for_user(user, day)
        self._uow.audit.record(
            "punch.create",
            user.id,
            {"direction": direction.value, "kiosk_id": kiosk_id, "event_id": event.id},
        )
        self._uow.commit()
        self._uow.refresh(event)
        return event

    def list_mine(self, user: User, limit: int = 50) -> list[PunchEvent]:
        return self._uow.punches.list_for_user(user.id, limit=limit)
