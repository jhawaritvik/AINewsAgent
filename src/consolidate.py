from __future__ import annotations
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import os
import html

from .news_types import NewsItem
from google import genai


def _normalize_url(url: str | None) -> str:
    return (url or "").strip().lower().rstrip("/")


def dedupe_items(items: List[NewsItem]) -> List[NewsItem]:
    seen: set[str] = set()
    result: List[NewsItem] = []
    for it in items:
        key = (_normalize_url(it.url), (it.title or "").strip().lower())
        if key in seen:
            continue
        seen.add(key)
        result.append(it)
    return result


def _source_weight_for(source: str | None, weights: Dict[str, float]) -> float:
    s = (source or "").strip().lower()
    if s.startswith("@"):
        return float(weights.get("twitter", 0.0))
    if s.startswith("r/"):
        return float(weights.get("reddit", 0.0))
    # Heuristic: treat everything else as RSS unless explicitly mapped
    return float(weights.get("rss", 0.0))


def rank_items(items: List[NewsItem], weights: Optional[Dict[str, float]] = None, now: Optional[datetime] = None) -> List[NewsItem]:
    if now is None:
        now = datetime.now(timezone.utc)
    weights = weights or {}
    def score_fn(it: NewsItem) -> float:
        age_hours = 0.0
        if it.published_at:
            age_hours = max(0.0, (now - it.published_at).total_seconds() / 3600.0)
        recency_bonus = max(0.0, 48.0 - age_hours)  # prefer last 2 days
        base = float(it.score or 0.0)
        source_w = _source_weight_for(getattr(it, "source", None), weights)
        return base + recency_bonus + source_w
    return sorted(items, key=score_fn, reverse=True)


def _make_llm_prompt_full_report(items: List[NewsItem], max_items: int = 40) -> str:
    limited = items[:max_items]
    lines = [
        "You are an expert AI news editor and technical report writer.",
        "Produce a FULL, self-contained daily report in **HTML5 only** (do not use Markdown).",
        "Constraints and format:",
        "- Output a valid, standalone HTML document: include <!DOCTYPE html>, <html>, <head>, and <body>.",
        "- Add a <head> with a <style> block for clean, modern email-friendly formatting:",
        "    * Font: system-ui or sans-serif.",
        "    * Light background (#f9f9f9) with card-like white sections and subtle shadows.",
        "    * Use padding, spacing, and <h1>/<h2> headings for readability.",
        "- At the top: include an <h1> titled 'AI Daily Report' and an **Executive Summary** (3–5 sentences).",
        "- Cluster and deduplicate: combine highly similar items into one topic section.",
        "- Each topic section should include:",
        "    * A short <h2> heading (the theme/topic).",
        "    * A descriptive summary (3–6 sentences).",
        "    * 2–4 key bullet takeaways (<ul><li>).",
        "    * At most one inline image if provided (with alt text).",
        "    * A 'Read more' link to the best single source.",
        "- At the end: add a 'Key Takeaways' section in bullet points.",
        "- Keep tone precise, professional, and neutral (no hype).",
        "- Ensure everything is self-contained—no external CSS, JS, or links except for sources.",
    ]
    for it in limited:
        published = it.published_at.isoformat() if it.published_at else ""
        image_part = f" image_url={it.image_url}" if getattr(it, "image_url", None) else ""
        summary_part = (it.summary or "").replace("\n", " ").strip()
        lines.append(
            f"- [source={it.source}] title={it.title} date={published} url={it.url}{image_part} summary={summary_part}"
        )
    return "\n".join(lines)


import time
from typing import Dict, Any, Optional

def _call_gemini(cfg: Dict[str, Any], prompt: str, max_retries: int = 3, delay_sec: float = 5.0) -> Optional[str]:
    attempt = 0
    while attempt < max_retries:
        try:
            api_key = cfg.get("api_key")
            if not api_key:
                print("❌ Missing Gemini API key in config.yaml")
                return None

            model = cfg.get("model", "gemini-2.5-flash")
            base_url = (cfg.get("base_url") or "").strip() or None

            print(f"⚡ _call_gemini(): Using model={model} (Attempt {attempt + 1})")
            print(f"⚡ API key present? {bool(api_key)} | Base URL={base_url}")

            client_args = {"api_key": api_key}
            if base_url:
                client_args["base_url"] = base_url

            client = genai.Client(**client_args)

            print("⚡ Sending request to Gemini…")
            resp = client.models.generate_content(
                model=model,
                contents=prompt
            )

            text = getattr(resp, "text", None)

            # Fallback: manually join candidates
            if not text and hasattr(resp, "candidates"):
                parts = []
                for cand in resp.candidates:
                    if hasattr(cand, "content") and getattr(cand.content, "parts", None):
                        for p in cand.content.parts:
                            if hasattr(p, "text") and p.text:
                                parts.append(p.text)
                    if hasattr(cand, "finish_reason"):
                        print(f"⚠️ Candidate finish_reason: {cand.finish_reason}")
                text = "\n".join(parts).strip() if parts else None

            if text:
                print("✅ Gemini call completed. Got text? True")
                return text
            else:
                print("⚠️ Gemini returned no text, retrying…")

        except Exception as e:
            print(f"❌ Gemini call failed: {e}")

        attempt += 1
        if attempt < max_retries:
            print(f"⏳ Waiting {delay_sec} seconds before retry…")
            time.sleep(delay_sec)
        else:
            print("⚠️ Max retries reached. Giving up.")

    return None

def _escape(s: str | None) -> str:
    return html.escape(s or "")


def _fallback_sections(items: List[NewsItem], max_items: int = 30) -> str:
    parts: list[str] = []
    for it in items[:max_items]:
        published = it.published_at.isoformat() if it.published_at else ""
        parts.append(
            f"<li>[{_escape(it.source)}] <a href=\"{_escape(it.url)}\">{_escape(it.title)}</a> <small>{_escape(published)}</small></li>"
        )
    return "<h2>Latest</h2><ul>" + "\n".join(parts) + "</ul>"


def make_report(items: List[NewsItem], config: Dict[str, Any]) -> str:
    """Return the raw LLM-generated full report (HTML or Markdown). Falls back to a simple HTML list."""
    items = dedupe_items(items)
    weights = (config.get("ranking", {}) or {}).get("source_weights", {})
    items = rank_items(items, weights=weights)
    llm_cfg = (config.get("llm") or {})
    use_llm = bool(llm_cfg.get("enabled"))
    if use_llm:
        print("⚡ Calling Gemini with", len(items), "items...")
        prompt = _make_llm_prompt_full_report(items, max_items=int(config.get("options", {}).get("max_items", 40)))
        text = _call_gemini(llm_cfg, prompt)
        print("⚡ Gemini returned:", "yes" if text else "no")
        if text:
            return text
    # Fallback: return a minimal HTML snippet
    return _fallback_sections(items)