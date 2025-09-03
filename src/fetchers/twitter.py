from typing import Iterable, List
from datetime import datetime, timezone
from urllib.parse import urlparse
import random
import re
import feedparser

from ..news_types import NewsItem

HANDLE_RE = re.compile(r"^(?:@)?([A-Za-z0-9_]{1,15})$")

def _extract_handle(account: str) -> str | None:
    text = (account or "").strip()
    if not text:
        return None
    m = HANDLE_RE.match(text)
    if m:
        return m.group(1)
    try:
        parsed = urlparse(text)
        path = (parsed.path or "/").strip("/")
        if not path:
            return None
        candidate = path.split("/")[0]
        m2 = HANDLE_RE.match(candidate)
        return m2.group(1) if m2 else None
    except Exception:
        return None

def fetch_from_twitter(
    accounts: Iterable[str],
    nitter_instances: Iterable[str] | None = None,
    max_items_per_account: int = 15,
) -> List[NewsItem]:
    items: List[NewsItem] = []
    instances = list(nitter_instances or [
        "https://nitter.net",
        "https://nitter.fdn.fr",
        "https://nitter.unixfox.eu",
        "https://nitter.poast.org",
    ])
    random.shuffle(instances)

    for account in accounts:
        handle = _extract_handle(account)
        if not handle:
            print(f"[Twitter] Invalid handle: {account}")
            continue

        feed = None
        for base in instances:
            try:
                rss_url = f"{base.rstrip('/')}/{handle}/rss"
                feed = feedparser.parse(rss_url)
                if getattr(feed, "entries", None):
                    break
            except Exception as e:
                print(f"[Twitter] Error fetching {handle} from {base}: {e}")
                continue

        if not feed or not getattr(feed, "entries", None):
            print(f"[Twitter] No entries found for @{handle}")
            continue

        source_title = feed.feed.get("title", f"@{handle}") if hasattr(feed, "feed") else f"@{handle}"
        count = 0
        effective_cap = int(max_items_per_account or 15)

        for entry in feed.entries:
            if count >= effective_cap:
                break

            title = entry.get("title") or entry.get("summary") or f"Tweet by @{handle}"
            link = entry.get("link") or ""

            # Parse published date
            published_at: datetime | None = None
            parsed = entry.get("published_parsed") or entry.get("updated_parsed")
            if parsed:
                published_at = datetime(*parsed[:6], tzinfo=timezone.utc)
            else:
                # fallback to now to avoid being dropped by lookback filter
                published_at = datetime.now(timezone.utc)

            items.append(NewsItem(
                title=title,
                url=link,
                source=source_title,
                published_at=published_at,
                summary=None,
                image_url=None,
                score=0.0,
            ))
            count += 1

    print(f"[Twitter] Fetched {len(items)} total tweets from {len(accounts)} accounts")
    return items
