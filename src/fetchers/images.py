from __future__ import annotations
from typing import Iterable
import requests
from bs4 import BeautifulSoup

from ..news_types import NewsItem


def _extract_og_image(html_text: str) -> str | None:
	soup = BeautifulSoup(html_text, "html.parser")
	# Common meta tags for preview images
	for attr, value in (
		("property", "og:image"),
		("name", "og:image"),
		("name", "twitter:image"),
		("property", "twitter:image"),
	):
		tag = soup.find("meta", attrs={attr: value})
		if tag:
			content = tag.get("content")
			if content and content.strip():
				return content.strip()
	return None


def attach_og_images(items: Iterable[NewsItem], timeout: int = 10) -> None:
	"""Mutates items in-place, setting image_url where available via OpenGraph.
	Skips items without a URL or already having an image_url.
	"""
	session = requests.Session()
	headers = {"User-Agent": "AINewsAgent/0.1 (+https://example.com)"}
	for it in items:
		if not it.url or it.image_url:
			continue
		try:
			resp = session.get(it.url, headers=headers, timeout=timeout)
			if resp.status_code != 200 or not resp.text:
				continue
			img = _extract_og_image(resp.text)
			if img:
				it.image_url = img
		except Exception:
			continue


