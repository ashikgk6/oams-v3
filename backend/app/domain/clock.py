from datetime import date, datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


class IstClock:
    def now(self) -> datetime:
        return datetime.now(IST)

    def today(self) -> date:
        return self.now().date()
