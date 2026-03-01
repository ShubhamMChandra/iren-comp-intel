# Why: Detects compute-intensive research at AI labs
# Deps: BaseCollector, feedparser, Company model
# How: ArXiv API RSS for papers by affiliation in cs.LG/cs.AI

import time
from urllib.parse import quote

import feedparser

from collectors.base import BaseCollector
from database.models import Company

SCALE_KEYWORDS = [
    "large-scale", "billion parameter", "gpu", "cluster",
    "distributed training", "scaling", "infrastructure",
    "compute", "h100", "h200", "b200", "tpu",
    "pretraining", "pre-training", "fine-tuning", "finetuning",
    "training run", "inference", "serving",
    "mixture of experts", "moe", "rlhf", "alignment",
]


class ArXivCollector(BaseCollector):
    collector_name = "arxiv"

    def collect(self) -> None:
        companies = (
            self.session.query(Company)
            .filter(Company.arxiv_org.isnot(None))
            .all()
        )
        print(f"[arxiv] Scanning {len(companies)} companies with ArXiv affiliations...")

        for company in companies:
            try:
                self._collect_for_company(company)
            except Exception as e:
                print(f"[arxiv] Error for {company.name}: {e}")
            time.sleep(3)

        self.finish()

    def _collect_for_company(self, company: Company) -> None:
        query = f"all:{quote(company.arxiv_org)}+AND+(cat:cs.LG+OR+cat:cs.AI+OR+cat:cs.CL)"
        url = (
            f"http://export.arxiv.org/api/query?"
            f"search_query={query}&sortBy=submittedDate"
            f"&sortOrder=descending&max_results=10"
        )
        feed = feedparser.parse(url)

        for entry in feed.entries:
            try:
                title = entry.get("title", "").replace("\n", " ").strip()
                summary = entry.get("summary", "").replace("\n", " ").strip()
                link = entry.get("link", "")
                searchable = f"{title} {summary}".lower()

                if not any(kw in searchable for kw in SCALE_KEYWORDS):
                    continue

                self._create_signal(
                    company_id=company.id,
                    signal_type="ai_initiative",
                    title=f"[ArXiv] {title[:400]}",
                    summary=f"Research paper from {company.name}: {summary[:200]}",
                    source_url=link,
                    source_type="blog",
                    magnitude=1.0,
                )
            except Exception as e:
                print(f"[arxiv] Error processing paper '{entry.get('title', '?')[:60]}': {e}")
