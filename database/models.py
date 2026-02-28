# Why: Defines all database tables as ORM classes
# Deps: SQLAlchemy Column types, relationships
# How: DeclarativeBase subclasses mapped to SQLite tables

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    company_type = Column(String(50), nullable=False)  # "prospect" or "competitor"
    industry = Column(String(255), default="")
    website = Column(String(500), default="")
    description = Column(Text, default="")
    hq_location = Column(String(255), default="")
    employee_count = Column(Integer, nullable=True)
    founded_year = Column(Integer, nullable=True)
    is_public = Column(Boolean, default=False)
    ticker = Column(String(20), nullable=True)
    sec_cik = Column(String(20), nullable=True)

    # Competitor-specific fields (null for prospects)
    capacity_mw = Column(Float, nullable=True)
    gpu_count = Column(Integer, nullable=True)
    known_pricing = Column(Text, nullable=True)

    last_funding_amount = Column(Float, nullable=True)
    last_funding_date = Column(DateTime, nullable=True)
    total_funding = Column(Float, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    signals = relationship("Signal", back_populates="company", cascade="all, delete-orphan")
    scores = relationship("ProspectScore", back_populates="company", cascade="all, delete-orphan")
    briefs = relationship("ProspectBrief", back_populates="company", cascade="all, delete-orphan")
    competitor_events = relationship("CompetitorEvent", back_populates="company", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Company {self.name} ({self.company_type})>"


class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    signal_type = Column(String(50), nullable=False)
    title = Column(String(500), nullable=False)
    summary = Column(Text, default="")
    source_url = Column(String(1000), default="")
    source_type = Column(String(50), default="industry_news")
    magnitude = Column(Float, default=1.0)
    is_active = Column(Boolean, default=True)
    raw_data = Column(Text, nullable=True)
    embedding = Column(Text, nullable=True)
    detected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    company = relationship("Company", back_populates="signals")

    def __repr__(self):
        return f"<Signal {self.signal_type}: {self.title[:50]}>"


class ProspectScore(Base):
    __tablename__ = "prospect_scores"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    total_score = Column(Float, default=0.0)
    fundraising_score = Column(Float, default=0.0)
    funding_completed_score = Column(Float, default=0.0)
    hiring_score = Column(Float, default=0.0)
    ai_initiative_score = Column(Float, default=0.0)
    cloud_spend_score = Column(Float, default=0.0)
    outgrowing_score = Column(Float, default=0.0)

    scored_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    company = relationship("Company", back_populates="scores")

    def __repr__(self):
        return f"<ProspectScore {self.company_id}: {self.total_score:.1f}>"


class ProspectBrief(Base):
    __tablename__ = "prospect_briefs"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    brief_text = Column(Text, nullable=False)
    brief_type = Column(String(50), default="sales_brief")
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    company = relationship("Company", back_populates="briefs")

    def __repr__(self):
        return f"<ProspectBrief {self.company_id} ({self.brief_type})>"


class CompetitorEvent(Base):
    __tablename__ = "competitor_events"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    event_type = Column(String(50), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, default="")
    source_url = Column(String(1000), default="")
    detected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    company = relationship("Company", back_populates="competitor_events")

    def __repr__(self):
        return f"<CompetitorEvent {self.event_type}: {self.title[:50]}>"
