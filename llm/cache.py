"""
llm/cache.py
Disk-backed response cache — keyed by student ID + data hash.
Cached tokens don't count toward Groq/NIM rate limits.
"""

import json
import diskcache
from pathlib import Path

CACHE_DIR = Path(".cache/llm_responses")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

_cache = diskcache.Cache(str(CACHE_DIR))


def get_cached(key: str) -> dict | None:
    try:
        value = _cache.get(key)
        if value is not None:
            return json.loads(value)
    except Exception:
        pass
    return None


def set_cached(key: str, value: dict, expire: int = 86400 * 7) -> None:
    """Cache for 7 days by default."""
    try:
        _cache.set(key, json.dumps(value), expire=expire)
    except Exception:
        pass


def invalidate(key: str) -> None:
    try:
        _cache.delete(key)
    except Exception:
        pass


def clear_all() -> None:
    try:
        _cache.clear()
    except Exception:
        pass


def cache_stats() -> dict:
    return {
        "size": len(_cache),
        "volume_bytes": _cache.volume(),
    }
