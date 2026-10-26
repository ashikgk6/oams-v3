from __future__ import annotations

from datetime import date

from app.domain.protocols import UnitOfWork
from app.models import Holiday, OfficeSettings, User


class AdminError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AdminApplicationService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def get_settings(self) -> OfficeSettings:
        return self._uow.settings.get_or_create()

    def update_settings(self, actor: User, data: dict) -> OfficeSettings:
        settings = self._uow.settings.get_or_create()
        for key, value in data.items():
            setattr(settings, key, value)
        self._uow.settings.save(settings)
        self._uow.audit.record("settings.update", actor.id, data)
        self._uow.commit()
        self._uow.refresh(settings)
        return settings

    def list_holidays(self) -> list[Holiday]:
        return self._uow.settings.list_holidays()

    def add_holiday(self, actor: User, day: date, name: str) -> Holiday:
        if self._uow.settings.is_holiday(day):
            raise AdminError("Holiday exists")
        row = self._uow.settings.add_holiday(Holiday(date=day, name=name))
        self._uow.audit.record(
            "holiday.create", actor.id, {"date": str(day), "name": name}
        )
        self._uow.commit()
        self._uow.refresh(row)
        return row

    def delete_holiday(self, actor: User, holiday_id: int) -> None:
        if not self._uow.settings.delete_holiday(holiday_id):
            raise AdminError("Not found", 404)
        self._uow.audit.record("holiday.delete", actor.id, {"id": holiday_id})
        self._uow.commit()
