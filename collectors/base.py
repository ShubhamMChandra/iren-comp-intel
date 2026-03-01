# Why: Shared session, dedup, logging for collectors
# Deps: DB session, Signal model, embeddings
# How: Subclasses override collect(), use _create_signal()

from datetime import datetime, timezone

import feedparser
import requests

from ai.embeddings import (
    deserialize_embedding,
    get_embedding,
    is_semantically_duplicate,
    serialize_embedding,
)
from database.db import get_session
from database.models import Signal


_FETCH_TIMEOUT = 8
_FETCH_HEADERS = {"User-Agent": "IrenIntel/1.0 (research platform)"}


def fetch_feed(url: str) -> feedparser.FeedParserDict:
    """Fetch an RSS/Atom feed with a hard timeout. Returns empty dict on failure."""
    try:
        resp = requests.get(url, timeout=_FETCH_TIMEOUT, headers=_FETCH_HEADERS)
        resp.raise_for_status()
        return feedparser.parse(resp.text)
    except Exception:
        return feedparser.FeedParserDict()


class BaseCollector:
    """Base class for all data collectors."""

    collector_name: str = "base"

    def __init__(self):
        self.session = get_session()
        self.signals_created = 0
        self.semantic_dupes_caught = 0

    def fetch_feed(self, url: str) -> feedparser.FeedParserDict:
        """Fetch an RSS/Atom feed with a hard timeout."""
        return fetch_feed(url)

    def collect(self):
        """Override in subclasses. Main entry point for data collection."""
        raise NotImplementedError

    def _signal_exists(self, company_id: int, title: str) -> bool:
        """Check if we already have a signal with this exact title for this company."""
        return (
            self.session.query(Signal)
            .filter(Signal.company_id == company_id, Signal.title == title)
            .first()
            is not None
        )

    def _is_semantic_duplicate(self, company_id: int, title: str) -> tuple[bool, list[float] | None]:
        """
        Check if a signal is semantically similar to existing ones.
        Returns (is_duplicate, embedding) so we can store the embedding if not a dupe.
        """
        new_emb = get_embedding(title)
        if new_emb is None:
            return False, None

        existing = (
            self.session.query(Signal.embedding)
            .filter(Signal.company_id == company_id, Signal.embedding.isnot(None))
            .all()
        )

        existing_embeddings = []
        for (raw,) in existing:
            emb = deserialize_embedding(raw)
            if emb is not None:
                existing_embeddings.append(emb)

        if existing_embeddings and is_semantically_duplicate(new_emb, existing_embeddings):
            return True, new_emb

        return False, new_emb

    def _create_signal(
        self,
        company_id: int,
        signal_type: str,
        title: str,
        summary: str = "",
        source_url: str = "",
        source_type: str = "industry_news",
        magnitude: float = 1.0,
        is_active: bool = True,
        raw_data: str = None,
        detected_at: datetime = None,
    ) -> Signal | None:
        """Create a signal if it doesn't already exist. Returns the Signal or None if duplicate."""
        if self._signal_exists(company_id, title):
            return None

        is_dupe, embedding = self._is_semantic_duplicate(company_id, title)
        if is_dupe:
            self.semantic_dupes_caught += 1
            return None

        signal = Signal(
            company_id=company_id,
            signal_type=signal_type,
            title=title,
            summary=summary,
            source_url=source_url,
            source_type=source_type,
            magnitude=magnitude,
            is_active=is_active,
            raw_data=raw_data,
            embedding=serialize_embedding(embedding),
            detected_at=detected_at or datetime.now(timezone.utc),
        )
        self.session.add(signal)
        self.signals_created += 1
        return signal

    def finish(self):
        """Commit all changes and close the session."""
        self.session.commit()
        msg = f"[{self.collector_name}] Created {self.signals_created} new signals."
        if self.semantic_dupes_caught > 0:
            msg += f" ({self.semantic_dupes_caught} semantic duplicates filtered)"
        print(msg)
        self.session.close()
