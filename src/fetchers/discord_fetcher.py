from datetime import datetime, timezone
from typing import Iterable, List, Optional
import requests
from ..news_types import NewsItem

API_BASE = "https://discord.com/api/v10"
USER_AGENT = "AINewsAgent/0.1 (discord-fetcher)"


def _auth_headers(bot_token: str) -> dict:
    return {
        "Authorization": f"Bot {bot_token}",
        "User-Agent": USER_AGENT,
    }


def _get_channel_info(session: requests.Session, channel_id: str) -> Optional[dict]:
    try:
        r = session.get(f"{API_BASE}/channels/{channel_id}")
        if r.status_code == 200:
            return r.json()
        return None
    except Exception:
        return None


def _get_recent_messages(session: requests.Session, channel_id: str, limit: int) -> list[dict]:
    try:
        r = session.get(f"{API_BASE}/channels/{channel_id}/messages", params={"limit": limit})
        if r.status_code == 200:
            return r.json()
        return []
    except Exception:
        return []


def fetch_from_discord(bot_token: str, channel_ids: Iterable[str], per_channel_limit: int = 50, timeout: int = 15) -> List[NewsItem]:
    if not bot_token or not channel_ids:
        return []
    session = requests.Session()
    session.headers.update(_auth_headers(bot_token))
    session.timeout = timeout

    items: List[NewsItem] = []

    for channel_id in channel_ids:
        channel_info = _get_channel_info(session, channel_id)
        channel_name = channel_info.get("name") if isinstance(channel_info, dict) else None
        guild_id = channel_info.get("guild_id") if isinstance(channel_info, dict) else None
        source_name = f"Discord #{channel_name}" if channel_name else "Discord"

        messages = _get_recent_messages(session, channel_id, per_channel_limit)
        for msg in messages:
            content: str = msg.get("content") or ""
            if not content.strip():
                continue
            message_id = msg.get("id")
            ts = msg.get("timestamp")
            published_at: Optional[datetime] = None
            try:
                if ts:
                    published_at = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    if published_at.tzinfo is None:
                        published_at = published_at.replace(tzinfo=timezone.utc)
            except Exception:
                published_at = None

            title = content.strip().splitlines()[0]
            if len(title) > 120:
                title = title[:117] + "..."

            url = None
            if guild_id and message_id:
                url = f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"

            items.append(NewsItem(
                title=title or "Discord message",
                url=url or "",
                source=source_name,
                published_at=published_at,
                summary=content if len(content) <= 500 else content[:497] + "...",
                image_url=None,
                score=0.0,
            ))

    return items
