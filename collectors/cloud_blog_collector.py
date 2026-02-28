# Why: Detects cloud usage and AI workloads from provider blogs
# Deps: BaseCollector, feedparser, Company model
# How: AWS/GCP/Azure ML blog RSS matched against tracked companies

import feedparser

from collectors.base import BaseCollector
from database.models import Company

CLOUD_BLOG_FEEDS = [
    "https://aws.amazon.com/blogs/machine-learning/feed/",
    "https://cloud.google.com/blog/products/ai-machine-learning/rss",
    "https://azure.microsoft.com/en-us/blog/tag/ai/feed/",
]

CLOUD_SPEND_KEYWORDS = ["cost", "pricing", "savings", "optimization"]


class CloudBlogCollector(BaseCollector):
    collector_name = "cloud_blogs"

    def collect(self) -> None:
        prospects = (
            self.session.query(Company)
            .filter(Company.company_type == "prospect")
            .all()
        )
        print(f"[cloud_blogs] Scanning cloud blogs for {len(prospects)} prospects...")

        for feed_url in CLOUD_BLOG_FEEDS:
            try:
                self._process_feed(feed_url, prospects)
            except Exception as e:
                print(f"[cloud_blogs] Error fetching {feed_url}: {e}")

        self.finish()

    def _process_feed(self, feed_url: str, prospects: list[Company]) -> None:
        feed = feedparser.parse(feed_url)

        for entry in feed.entries[:30]:
            try:
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                link = entry.get("link", "")
                text = f"{title} {summary}".lower()

                for company in prospects:
                    if company.name.lower() not in text:
                        continue

                    signal_type = self._classify(title)
                    self._create_signal(
                        company_id=company.id,
                        signal_type=signal_type,
                        title=f"[Cloud Blog] {title[:400]}",
                        summary=summary[:200],
                        source_url=link,
                        source_type="industry_news",
                        magnitude=1.0,
                    )
            except Exception as e:
                print(f"[cloud_blogs] Error processing entry '{entry.get('title', '?')[:60]}': {e}")

    def _classify(self, title: str) -> str:
        if any(kw in title.lower() for kw in CLOUD_SPEND_KEYWORDS):
            return "cloud_spend"
        return "ai_initiative"
