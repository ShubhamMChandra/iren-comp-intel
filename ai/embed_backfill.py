"""
Backfill embeddings for all existing signals that don't have one.

Usage:
    python -m ai.embed_backfill           # embed all signals missing embeddings
    python -m ai.embed_backfill --force   # re-embed everything (overwrites existing)
"""

import sys
import time

from ai.embeddings import get_embeddings_batch, serialize_embedding, _check_ollama
from database.db import get_session, init_db
from database.models import Signal

BATCH_SIZE = 50


def backfill_embeddings(force: bool = False):
    init_db()

    if not _check_ollama():
        print("Ollama is not running. Start it with: ollama serve")
        print("Then pull the model: ollama pull nomic-embed-text")
        return

    session = get_session()
    try:
        query = session.query(Signal)
        if not force:
            query = query.filter(Signal.embedding.is_(None))

        signals = query.all()
        total = len(signals)

        if total == 0:
            print("All signals already have embeddings.")
            return

        print(f"Embedding {total} signals in batches of {BATCH_SIZE}...")

        embedded = 0
        failed = 0

        for i in range(0, total, BATCH_SIZE):
            batch = signals[i:i + BATCH_SIZE]
            titles = [s.title for s in batch]

            embeddings = get_embeddings_batch(titles)

            for signal, emb in zip(batch, embeddings):
                if emb is not None:
                    signal.embedding = serialize_embedding(emb)
                    embedded += 1
                else:
                    failed += 1

            session.commit()

            progress = min(i + BATCH_SIZE, total)
            print(f"  {progress}/{total} processed ({embedded} embedded, {failed} failed)")

            time.sleep(0.1)

        print(f"\nDone. {embedded} signals embedded, {failed} failed.")
    finally:
        session.close()


if __name__ == "__main__":
    force = "--force" in sys.argv
    backfill_embeddings(force=force)
