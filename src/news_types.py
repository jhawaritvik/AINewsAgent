from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class NewsItem:
    title: str
    url: str
    source: str
    published_at: Optional[datetime]
    summary: Optional[str]
    image_url: Optional[str]
    score: float = 0.0
