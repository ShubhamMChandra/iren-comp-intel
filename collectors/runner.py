# Why: CLI orchestrator for all data collectors
# Deps: init_db, all collector classes
# How: Instantiates and runs collectors by name

import sys
import time

from database.db import init_db
from collectors.arxiv_collector import ArXivCollector
from collectors.ats_collector import ATSCollector
from collectors.cloud_blog_collector import CloudBlogCollector
from collectors.competitive_intel_collector import CompetitiveIntelCollector
from collectors.earnings_collector import EarningsCollector
from collectors.edgar_rss_collector import EdgarRSSCollector
from collectors.peeringdb_collector import PeeringDBCollector
from collectors.press_release_collector import PressReleaseCollector
from collectors.trends_collector import TrendsCollector
from collectors.funding_collector import FundingCollector
from collectors.github_collector import GitHubCollector
from collectors.hn_collector import HNCollector
from collectors.jobs_collector import JobsCollector
from collectors.news_collector import NewsCollector
from collectors.sec_collector import SECCollector

COLLECTORS = {
    "news": NewsCollector,
    "jobs": JobsCollector,
    "sec": SECCollector,
    "funding": FundingCollector,
    "ats": ATSCollector,
    "earnings": EarningsCollector,
    "github": GitHubCollector,
    "arxiv": ArXivCollector,
    "hn": HNCollector,
    "cloud_blogs": CloudBlogCollector,
    "competitive_intel": CompetitiveIntelCollector,
    "press_releases": PressReleaseCollector,
    "edgar_rss": EdgarRSSCollector,
    "peeringdb": PeeringDBCollector,
    "trends": TrendsCollector,
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
