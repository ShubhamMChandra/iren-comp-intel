# Why: CLI orchestrator for all data collectors
# Deps: init_db, all collector classes
# How: Instantiates and runs collectors by name

import sys
import time

from database.db import init_db
from collectors.news_collector import NewsCollector
from collectors.jobs_collector import JobsCollector
from collectors.sec_collector import SECCollector
from collectors.funding_collector import FundingCollector

COLLECTORS = {
    "news": NewsCollector,
    "jobs": JobsCollector,
    "sec": SECCollector,
    "funding": FundingCollector,
}


def run_collectors(names: list[str] | None = None):
    """Run specified collectors (or all if none specified)."""
    init_db()

    to_run = names or list(COLLECTORS.keys())
    print(f"Running collectors: {', '.join(to_run)}")
    print("=" * 60)

    for name in to_run:
        collector_cls = COLLECTORS.get(name)
        if not collector_cls:
            print(f"Unknown collector: {name}")
            continue

        print(f"\n--- {name.upper()} COLLECTOR ---")
        start = time.time()

        try:
            collector = collector_cls()
            collector.collect()
        except Exception as e:
            print(f"[{name}] FAILED: {e}")

        elapsed = time.time() - start
        print(f"[{name}] Completed in {elapsed:.1f}s")

    print("\n" + "=" * 60)
    print("Collection complete.")


if __name__ == "__main__":
    args = sys.argv[1:]
    run_collectors(args if args else None)
