from typing import Iterable, List
from datetime import datetime, timezone
import feedparser
from dateutil import parser as date_parser
from ..news_types import NewsItem


def parse_datetime(value) -> datetime | None:
    if not value:
        return None
    try:
        if isinstance(value, str):
            dt = date_parser.parse(value)
        else:
            # feedparser returns a time.struct_time sometimes
            dt = datetime(*value[:6])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def fetch_from_rss(urls: Iterable[str], max_items_per_feed: int = 15) -> List[NewsItem]:
    items: List[NewsItem] = []
    for url in urls:
        try:
            feed = feedparser.parse(url)
            source_title = feed.feed.get("title", "RSS") if hasattr(feed, "feed") else "RSS"
            # Enforce hard cap per feed
            cap = max(0, min(int(max_items_per_feed or 0), 15))
            for entry in getattr(feed, "entries", [])[:cap]:
                title = entry.get("title", "Untitled")
                link = entry.get("link") or entry.get("id") or ""
                summary = entry.get("summary") or entry.get("description")
                published = entry.get("published") or entry.get("updated") or entry.get("created")
                published_at = parse_datetime(published)
                items.append(NewsItem(
                    title=title,
                    url=link,
                    source=source_title,
                    published_at=published_at,
                    summary=summary,
                    image_url=None,
                    score=0.0,
                ))
        except Exception:
            continue
    return items
