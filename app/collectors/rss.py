import socket
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import feedparser
from bs4 import BeautifulSoup

socket.setdefaulttimeout(10)

FEEDS = {
    "BBC World": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "Dawn": "https://www.dawn.com/feeds/home",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "TechCrunch": "https://techcrunch.com/feed/",
}


@dataclass
class Article:
    title: str
    link: str
    summary: str
    source: str
    published: Optional[datetime] = None
    extra: dict = field(default_factory=dict)


def clean_html(text: str) -> str:
    """HTML tags hata kar plain text return karta hai."""
    if not text:
        return ""
    return BeautifulSoup(text, "html.parser").get_text(" ", strip=True)


def parse_date(entry) -> Optional[datetime]:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        return datetime(*parsed[:6])
    return None


def fetch_feed(source: str, url: str, limit: int = 10) -> list[Article]:
    """Ek feed se articles laata hai. Fail ho to khali list return karta hai."""
    try:
        feed = feedparser.parse(url)
    except Exception as e:
        print(f"[ERROR] {source}: {e}")
        return []

    if not feed.entries:
        print(f"[WARN] {source}: koi article nahi mila")
        return []

    articles = []
    for entry in feed.entries[:limit]:
        articles.append(
            Article(
                title=clean_html(entry.get("title", "")),
                link=entry.get("link", ""),
                summary=clean_html(entry.get("summary", "")),
                source=source,
                published=parse_date(entry),
            )
        )
    return articles


def collect_all(limit_per_feed: int = 10) -> list[Article]:
    """Saari feeds se articles collect karta hai."""
    all_articles: list[Article] = []
    for source, url in FEEDS.items():
        all_articles.extend(fetch_feed(source, url, limit_per_feed))
    return all_articles


if __name__ == "__main__":
    articles = collect_all(limit_per_feed=5)
    print(f"\nTotal articles: {len(articles)}\n")
    for a in articles:
        print(f"[{a.source}] {a.title}")
        print(f"   {a.link}")
        print(f"   {a.published}\n")
