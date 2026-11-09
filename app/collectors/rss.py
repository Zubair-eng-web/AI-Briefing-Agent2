import socket
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import feedparser
from bs4 import BeautifulSoup

socket.setdefaulttimeout(10)

# Kuch sites (jaise Al Jazeera) feedparser ke default User-Agent ko block karti hain
feedparser.USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
RETRY_DELAY = 1.5

FEEDS = {
    "BBC World": "https://feeds.bbci.co.uk/news/world/rss.xml",
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
    feed = None
    for attempt in range(2):  # ek baar retry: temporary network hiccup se bachne ke liye
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            print(f"[ERROR] {source}: {e}")
            feed = None
        if feed is not None and feed.entries:
            break
        if attempt == 0:
            time.sleep(RETRY_DELAY)

    if feed is None or not feed.entries:
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
