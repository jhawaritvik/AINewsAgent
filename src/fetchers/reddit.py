from typing import Iterable, List
from datetime import datetime, timezone
import requests
from ..news_types import NewsItem

USER_AGENT = "AINewsAgent/0.1 (contact: you@example.com)"


def fetch_from_reddit(subreddits: Iterable[str], limit: int = 15, timeout: int = 15) -> List[NewsItem]:
    items: List[NewsItem] = []
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    for sub in subreddits:
        # Enforce hard cap per subreddit
        per_limit = max(0, min(int(limit or 0), 15))
        url = f"https://www.reddit.com/r/{sub}/new.json?limit={per_limit}"
        try:
            resp = session.get(url, timeout=timeout)
            if resp.status_code != 200:
                continue
            data = resp.json()
            for child in data.get("data", {}).get("children", []):
                post = child.get("data", {})
                title = post.get("title", "Untitled")
                permalink = post.get("permalink", "")
                link = f"https://www.reddit.com{permalink}" if permalink else post.get("url_overridden_by_dest") or post.get("url") or ""
                created_utc = post.get("created_utc")
                published_at = datetime.fromtimestamp(created_utc, tz=timezone.utc) if created_utc else None
                summary = post.get("selftext") or None
                score = float(post.get("score", 0))
                items.append(NewsItem(
                    title=title,
                    url=link,
                    source=f"r/{sub}",
                    published_at=published_at,
                    summary=summary,
                    image_url=None,
                    score=score,
                ))
        except Exception:
            continue
    return items
