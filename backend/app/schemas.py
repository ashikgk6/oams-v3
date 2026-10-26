from datetime import date, datetime, time
from typing import Optional

from pydantic import BaseModel, Field

from app.models import (
    AttendanceStatus,
    LeaveType,
    PunchDirection,
    RequestStatus,
    UserRole,
)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    name: str
    user_id: int


class LoginIn(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: UserRole
    team_id: Optional[int] = None
    team_name: Optional[str] = None
    active: bool

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    name: str
    email: str
    password: str = "Welcome@123"
    role: UserRole = UserRole.employee
    team_id: Optional[int] = None


class TeamCreate(BaseModel):
    name: str
    manager_id: Optional[int] = None


class TeamOut(BaseModel):
    id: int
    name: str
    manager_id: Optional[int] = None

    model_config = {"from_attributes": True}


class OfficeSettingsOut(BaseModel):
    office_name: str
    timezone: str
    shift_start: time
    shift_end: time
    grace_minutes: int
    half_day_after: time
    min_half_day_minutes: int

    model_config = {"from_attributes": True}


class OfficeSettingsUpdate(BaseModel):
    office_name: Optional[str] = None
    shift_start: Optional[time] = None
    shift_end: Optional[time] = None
    grace_minutes: Optional[int] = None
    half_day_after: Optional[time] = None
    min_half_day_minutes: Optional[int] = None


class KioskCreate(BaseModel):
    name: str


class KioskOut(BaseModel):
    id: int
    name: str
    pair_code: Optional[str] = None
    paired_at: Optional[datetime] = None
    active: bool

    model_config = {"from_attributes": True}


class KioskPairIn(BaseModel):
    pair_code: str


class KioskPairOut(BaseModel):
    kiosk_id: int
    name: str
    device_secret: str


class QrPayloadOut(BaseModel):
    token: str
    expires_in: int
    kiosk_name: str


class PunchIn(BaseModel):
    qr_token: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_meters: float = Field(gt=0, le=10000)


class PunchOut(BaseModel):
    id: int
    direction: PunchDirection
    ts: datetime
    message: str


class AttendanceDayOut(BaseModel):
    date: date
    status: AttendanceStatus
    first_in: Optional[datetime] = None
    last_out: Optional[datetime] = None
    work_minutes: Optional[int] = None
    late_minutes: Optional[int] = None

    model_config = {"from_attributes": True}


class LeaveCreate(BaseModel):
    leave_type: LeaveType
    start_date: date
    end_date: date
    reason: Optional[str] = None


class LeaveOut(BaseModel):
    id: int
    user_id: int
    user_name: Optional[str] = None
    leave_type: LeaveType
    start_date: date
    end_date: date
    reason: Optional[str] = None
    status: RequestStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class DecisionIn(BaseModel):
    approve: bool


class CorrectionCreate(BaseModel):
    date: date
    requested_in: Optional[datetime] = None
    requested_out: Optional[datetime] = None
    reason: str = Field(min_length=3)


class CorrectionOut(BaseModel):
    id: int
    user_id: int
    user_name: Optional[str] = None
    date: date
    requested_in: Optional[datetime] = None
    requested_out: Optional[datetime] = None
    reason: str
    status: RequestStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class DisplayTokenCreate(BaseModel):
    label: str = "Reception TV"


class DisplayTokenOut(BaseModel):
    id: int
    label: str
    token: Optional[str] = None  # only returned on create
    token_prefix: str
    revoked_at: Optional[datetime] = None
    created_at: datetime
    display_path: Optional[str] = None


class HolidayCreate(BaseModel):
    date: date
    name: str


class HolidayOut(BaseModel):
    id: int
    date: date
    name: str

    model_config = {"from_attributes": True}


class WallboardPerson(BaseModel):
    name: str
    team: Optional[str] = None
    in_time: Optional[str] = None
    late_minutes: Optional[int] = None


class WallboardOut(BaseModel):
    office_name: str
    timezone: str
    date: str
    clock: str
    is_working_day: bool
    closed_message: Optional[str] = None
    counts: dict
    in_now: list[WallboardPerson]
    late_today: list[WallboardPerson]
    on_leave: list[WallboardPerson]
    not_in: list[WallboardPerson]


class TeamTodayOut(BaseModel):
    team_id: int
    team_name: str
    members: list[dict]


class AuditOut(BaseModel):
    id: int
    actor_id: Optional[int]
    action: str
    payload: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
