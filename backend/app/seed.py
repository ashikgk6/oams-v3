from sqlalchemy.orm import Session

from app.config import get_settings
from app.infrastructure.repositories import SqlSettingsRepository
from app.models import Team, User, UserRole
from app.security import hash_password

settings = get_settings()


def seed_database(db: Session) -> None:
    """Idempotent demo data for local/dev boots."""
    office = SqlSettingsRepository(db).get_or_create()
    if not office.office_name:
        office.office_name = settings.app_name
    db.commit()

    if db.query(User).filter(User.email == settings.seed_admin_email).first():
        return

    eng = db.query(Team).filter(Team.name == "Engineering").first()
    if not eng:
        eng = Team(name="Engineering")
        db.add(eng)
        db.flush()

    admin = User(
        name="Office Admin",
        email=settings.seed_admin_email,
        hashed_password=hash_password(settings.seed_admin_password),
        role=UserRole.admin,
        team_id=eng.id,
        active=True,
    )
    db.add(admin)
    db.flush()

    mgr = User(
        name="Demo Manager",
        email="manager@office.local",
        hashed_password=hash_password("manager123"),
        role=UserRole.manager,
        team_id=eng.id,
        active=True,
    )
    db.add(mgr)
    db.flush()
    eng.manager_id = mgr.id

    db.add(
        User(
            name="Demo Employee",
            email="employee@office.local",
            hashed_password=hash_password("employee123"),
            role=UserRole.employee,
            team_id=eng.id,
            active=True,
        )
    )

    if not db.query(Team).filter(Team.name == "People Ops").first():
        db.add(Team(name="People Ops", manager_id=admin.id))

    db.commit()
