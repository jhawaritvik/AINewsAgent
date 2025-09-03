import os
from typing import Any, Dict
import yaml


def load_config(config_path: str = None) -> Dict[str, Any]:
    if config_path is None:
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
    if not os.path.isfile(config_path):
        # Fall back to example to help initial run
        example_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.example.yaml")
        path_to_use = example_path if os.path.isfile(example_path) else config_path
    else:
        path_to_use = config_path

    with open(path_to_use, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    # --- Directly load specific environment variables ---
    if "llm" in data and "api_key_env" in data["llm"]:
        data["llm"]["api_key"] = os.getenv(data["llm"]["api_key_env"])
        
    if "email" in data and "smtp" in data["email"]:
        smtp_cfg = data["email"]["smtp"]
        if "username_env" in smtp_cfg:
            smtp_cfg["username"] = os.getenv(smtp_cfg["username_env"])
        if "password_env" in smtp_cfg:
            smtp_cfg["password"] = os.getenv(smtp_cfg["password_env"])
    
    # Defaults
    data.setdefault("sources", {})
    data["sources"].setdefault("rss_urls", [])
    data["sources"].setdefault("reddit_subreddits", [])
    data["sources"].setdefault("twitter_accounts", [])
    # Moved nitter instances to config.yaml as the single source of truth
    if "nitter_instances" not in data["sources"] and "nitter_instances" not in data["sources"]:
        data["sources"]["nitter_instances"] = [
            "https://nitter.net",
            "https://nitter.fdn.fr",
            "https://nitter.unixfox.eu",
            "https://nitter.poast.org",
        ]
    data["sources"].setdefault("discord", {})
    data["sources"]["discord"].setdefault("enabled", False)
    data["sources"]["discord"].setdefault("bot_token", "")
    data["sources"]["discord"].setdefault("channel_ids", [])
    data["sources"]["discord"].setdefault("per_channel_limit", 50)

    data.setdefault("filters", {})
    data["filters"].setdefault("include_keywords", [])
    data["filters"].setdefault("exclude_domains", [])

    data.setdefault("options", {})
    data["options"].setdefault("max_items", 30)
    data["options"].setdefault("min_score", 0)
    data["options"].setdefault("fetch_images", True)
    data["options"].setdefault("fetch_timeout_sec", 15)

    # Additional controls to limit search space without losing sources
    data["options"].setdefault("lookback_hours", 0)
    data["options"].setdefault("keep_items_without_timestamp", True)
    data["options"].setdefault("rss_max_per_feed", 15)
    data["options"].setdefault("reddit_limit", 15)
    data["options"].setdefault("twitter_max_per_account", 15)

    # Ranking defaults
    data.setdefault("ranking", {})
    data["ranking"].setdefault("source_weights", {
        "twitter": 30.0,
        "reddit": 20.0,
        "rss": 10.0,
        "other": 0.0,
    })

    return data