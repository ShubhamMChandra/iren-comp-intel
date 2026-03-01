# Why: Manages SQLite connection and sessions
# Deps: SQLAlchemy engine, sessionmaker, config
# How: Creates engine once, vends sessions on demand

from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from config import DATABASE_URL
from database.models import Base

db_path = DATABASE_URL.replace("sqlite:///", "")
Path(db_path).parent.mkdir(parents=True, exist_ok=True)

_connect_args = {"check_same_thread": False, "timeout": 30} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine)


def _enable_wal(conn, _):
    """Enable WAL journal mode to allow concurrent reads/writes."""
    if DATABASE_URL.startswith("sqlite"):
        conn.execute("PRAGMA journal_mode=WAL")


if DATABASE_URL.startswith("sqlite"):
    from sqlalchemy import event
    event.listen(engine, "connect", _enable_wal)


def _migrate_prospect_briefs_nullable(conn) -> None:
    """Make prospect_briefs.company_id nullable if the existing schema has NOT NULL.

    SQLite doesn't support ALTER COLUMN, so we recreate the table when needed.
    Safe to run on every startup — checks column info first.
    """
    rows = conn.execute(text("PRAGMA table_info(prospect_briefs)")).fetchall()
    if not rows:
        return
    col = next((r for r in rows if r[1] == "company_id"), None)
    if col is None or col[3] == 0:
        return

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS prospect_briefs_new (
            id INTEGER PRIMARY KEY,
            company_id INTEGER REFERENCES companies(id),
            brief_text TEXT NOT NULL,
            brief_type VARCHAR(50) DEFAULT 'sales_brief',
            generated_at DATETIME
        )
    """))
    conn.execute(text("INSERT INTO prospect_briefs_new SELECT * FROM prospect_briefs"))
    conn.execute(text("DROP TABLE prospect_briefs"))
    conn.execute(text("ALTER TABLE prospect_briefs_new RENAME TO prospect_briefs"))


def init_db():
    """Create all tables and apply lightweight schema migrations."""
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        _migrate_prospect_briefs_nullable(conn)


def auto_seed_if_empty():
    """Seed companies if the DB is empty. Call after init_db(), not inside it."""
    session = SessionLocal()
    try:
        from database.models import Company
        if session.query(Company).count() == 0:
            from database.seed import seed_database
            seed_database()
    finally:
        session.close()


def get_session():
    """Return a new database session. Caller is responsible for closing it."""
    return SessionLocal()
