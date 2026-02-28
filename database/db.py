# Why: Manages SQLite connection and sessions
# Deps: SQLAlchemy engine, sessionmaker, config
# How: Creates engine once, vends sessions on demand

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import DATABASE_URL
from database.models import Base

db_path = DATABASE_URL.replace("sqlite:///", "")
Path(db_path).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    """Create all tables if they don't exist yet."""
    Base.metadata.create_all(engine)


def get_session():
    """Return a new database session. Caller is responsible for closing it."""
    return SessionLocal()
