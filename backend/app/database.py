from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()
_is_sqlite = settings.database_url.startswith("sqlite")

_engine_kwargs: dict = {
    "pool_pre_ping": not _is_sqlite,
    "connect_args": {"check_same_thread": False} if _is_sqlite else {},
}
if not _is_sqlite:
    # Sized for a few API workers hitting one Postgres instance.
    _engine_kwargs.update(pool_size=10, max_overflow=20, pool_recycle=1800)

engine = create_engine(settings.database_url, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
