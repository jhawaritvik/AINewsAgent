import argparse
from typing import List
from datetime import datetime, timedelta, timezone
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from .db import get_recipients

from .config import load_config
from .news_types import NewsItem
from .fetchers.rss import fetch_from_rss
from .fetchers.reddit import fetch_from_reddit
from .fetchers.discord_fetcher import fetch_from_discord
from .fetchers.twitter import fetch_from_twitter
from .consolidate import make_report
from .fetchers.images import attach_og_images


import os
import hmac
import hashlib

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretvalue")
SUPABASE_FUNCTION_URL = "https://dcbatzjctqnuvzxnndpj.functions.supabase.co/unsubscribe"

def generate_token(email: str) -> str:
    """Generate HMAC-SHA256 token from email using SECRET_KEY."""
    return hmac.new(
        SECRET_KEY.encode(),
        email.encode(),
        hashlib.sha256
    ).hexdigest()

def build_unsubscribe_link(email: str) -> str:
    """Build unsubscribe URL pointing to Supabase Edge Function."""
    token = generate_token(email)
    return f"{SUPABASE_FUNCTION_URL}?email={email}&token={token}"

def send_email(config, subject, html_content):
    import traceback

    email_cfg = config.get("email", {})
    if not email_cfg or not email_cfg.get("smtp"):
        print("⚠️ No email config found.")
        return

    recipients = get_recipients()
    if not recipients:
        print("⚠️ No recipients found in Supabase.")
        return

    smtp_cfg = email_cfg["smtp"]
    username = smtp_cfg.get("username")
    password = smtp_cfg.get("password")
    if not username or not password:
        print("❌ SMTP username or password not found.")
        return

    try:
        with smtplib.SMTP(smtp_cfg["host"], smtp_cfg["port"]) as server:
            server.ehlo()
            if smtp_cfg.get("use_tls", True):
                server.starttls()
                server.ehlo()
            server.login(username, password)

            for recipient in recipients:
                # Append personalized unsubscribe link to email body
                unsub_link = build_unsubscribe_link(recipient)
                body = f"""
                <html>
                <body style="font-family:Arial,sans-serif;line-height:1.5;color:#333;margin:0;padding:0;">
                    <div style="padding:20px;">
                    {html_content}
                    </div>
                    <div style="
                        position:fixed;
                        bottom:0;
                        width:100%;
                        background-color:#f9f9f9;
                        border-top:1px solid #eee;
                        text-align:center;
                        padding:15px 0;
                        box-shadow: 0 -2px 5px rgba(0,0,0,0.05);
                    ">
                    <a href="{unsub_link}" 
                        style="display:inline-block;padding:10px 20px;background-color:#f44336;color:white;text-decoration:none;border-radius:5px;font-weight:bold;">
                        Unsubscribe
                    </a>
                    </div>
                </body>
                </html>
                """


                msg = MIMEMultipart("alternative")
                msg["From"] = email_cfg["from"]
                msg["To"] = recipient
                msg["Subject"] = f"{email_cfg.get('subject_prefix', '')} {subject}"
                msg.attach(MIMEText(body, "html"))

                failed = server.sendmail(msg["From"], recipient, msg.as_string())
                if failed:
                    print(f"❌ Failed to send to {recipient}: {failed}")
                else:
                    print(f"✅ Email sent to {recipient}")

    except Exception as e:
        print("❌ Failed to send email!")
        print(f"Type: {type(e).__name__}")
        print(f"Args: {e.args}")
        traceback.print_exc()



def filter_items(items: List[NewsItem], include_keywords: list[str], exclude_domains: list[str]) -> List[NewsItem]:
    if not include_keywords and not exclude_domains:
        return items
    filtered: List[NewsItem] = []
    lower_keywords = [k.lower() for k in include_keywords]
    for item in items:
        url_lower = (item.url or "").lower()
        if any(dom.lower() in url_lower for dom in exclude_domains):
            continue
        if lower_keywords:
            text = f"{item.title} {item.summary or ''}".lower()
            if not any(k in text for k in lower_keywords):
                continue
        filtered.append(item)
    return filtered


def main():
    parser = argparse.ArgumentParser(description="AINewsAgent CLI")
    parser.add_argument("--once", action="store_true", help="Run one fetch and print a summary")
    parser.add_argument("--report", type=str, default=None, help="Write full LLM report (HTML or Markdown) to the given path")
    parser.add_argument("--config", type=str, default=None, help="Path to config.yaml")
    parser.add_argument("--send-email", action="store_true", help="Send the digest/report via email")
    args = parser.parse_args()

    config = load_config(args.config)

    # --- Fetching Logic ---
    rss_urls = config.get("sources", {}).get("rss_urls", [])
    reddit_subs = config.get("sources", {}).get("reddit_subreddits", [])
    discord_cfg = config.get("sources", {}).get("discord", {})
    twitter_accounts = config.get("sources", {}).get("twitter_accounts", [])
    nitter_instances = config.get("sources", {}).get("nitter_instances", [])

    items: List[NewsItem] = []
    if rss_urls:
        items.extend(fetch_from_rss(rss_urls, max_items_per_feed=int(config.get("options", {}).get("rss_max_per_feed", 15))))
    if reddit_subs:
        items.extend(fetch_from_reddit(reddit_subs, limit=int(config.get("options", {}).get("reddit_limit", 15)), timeout=config.get("options", {}).get("fetch_timeout_sec", 15)))
    if twitter_accounts:
        items.extend(fetch_from_twitter(twitter_accounts, nitter_instances=nitter_instances, max_items_per_account=int(config.get("options", {}).get("twitter_max_per_account", 15))))
    if discord_cfg.get("enabled"):
        token = discord_cfg.get("bot_token") or ""
        channel_ids = discord_cfg.get("channel_ids") or []
        per_limit = int(discord_cfg.get("per_channel_limit") or 50)
        if token and channel_ids:
            items.extend(fetch_from_discord(token, channel_ids, per_limit=per_limit, timeout=config.get("options", {}).get("fetch_timeout_sec", 15)))
        else:
            print("Discord enabled but missing bot_token or channel_ids; skipping.")

    # Time window filter
    opts = (config.get("options", {}) or {})
    if int(opts.get("lookback_hours", 0)) > 0:
        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=int(opts.get("lookback_hours", 0)))
        keep_untimed = bool(opts.get("keep_items_without_timestamp", True))
        items = [it for it in items if (it.published_at and it.published_at >= start) or (keep_untimed and it.published_at is None)]

    items = filter_items(items, config.get("filters", {}).get("include_keywords", []), config.get("filters", {}).get("exclude_domains", []))

    if bool(config.get("options", {}).get("fetch_images", False)):
        attach_og_images(items, timeout=config.get("options", {}).get("fetch_timeout_sec", 15))

    # Sort
    items.sort(key=lambda x: (x.published_at or 0, x.score), reverse=True)

    full_report = None

    if args.report or args.send_email:
        full_report = make_report(items, config)
    
    if args.once:
        print(f"Fetched {len(items)} items")
        for i, it in enumerate(items[:10], start=1):
            published = it.published_at.isoformat() if it.published_at else ""
            print(f"{i}. [{it.source}] {it.title} ({published}) -> {it.url}")
    
    if args.report and full_report:
        with open(args.report, "w", encoding="utf-8") as f:
            f.write(full_report)
        print(f"Wrote report to {args.report}")

    if args.send_email and full_report:
        subject = f"News Report - {datetime.now().strftime('%Y-%m-%d')}"
        send_email(config, subject, full_report)
    elif args.send_email and not full_report:
        print("⚠️ No report generated to send via email.")

    if not args.once and not args.report and not args.send_email:
        print("Use --once, --report, or --send-email.")


if __name__ == "__main__":
    main()
