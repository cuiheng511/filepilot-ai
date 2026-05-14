"""Search Cache — Cache search results for faster repeated queries"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from filepilot.core.config import SETTINGS_DIR

logger = logging.getLogger("filepilot.search_cache")

CACHE_DIR = SETTINGS_DIR / "search_cache"
CACHE_TTL_HOURS = 24
MAX_CACHE_ENTRIES = 500


def _hash_query(query: str) -> str:
    """Hash a search query for use as cache key"""
    return hashlib.sha256(query.encode("utf-8")).hexdigest()[:16]


def _cache_file(query_hash: str) -> Path:
    """Get cache file path for a query hash"""
    return CACHE_DIR / f"{query_hash}.json"


def get_cached_results(query: str) -> list[dict] | None:
    """Retrieve cached search results if available and not expired.

    Args:
        query: The search query string

    Returns:
        Cached results list, or None if not found/expired

    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    query_hash = _hash_query(query)
    cache_path = _cache_file(query_hash)

    if not cache_path.exists():
        return None

    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        cached_time = datetime.fromisoformat(data["cached_at"])

        # Check TTL
        if datetime.now() - cached_time > timedelta(hours=CACHE_TTL_HOURS):
            cache_path.unlink(missing_ok=True)
            return None

        logger.debug("Cache hit for query hash: %s", query_hash)
        return data["results"]  # type: ignore[no-any-return]

    except (json.JSONDecodeError, KeyError, OSError):
        logger.debug("Cache read failed for query hash: %s", query_hash)
        return None


def cache_results(query: str, results: list[dict]) -> None:
    """Cache search results for a query.

    Args:
        query: The search query string
        results: List of search result dicts

    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Prune old entries if cache is too large
    _prune_cache_if_needed()

    query_hash = _hash_query(query)
    cache_path = _cache_file(query_hash)

    try:
        data = {
            "query": query,
            "cached_at": datetime.now().isoformat(),
            "result_count": len(results),
            "results": results,
        }
        cache_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.debug("Cached %d results for query hash: %s", len(results), query_hash)
    except OSError:
        logger.warning("Failed to write search cache to %s", cache_path)


def _prune_cache_if_needed() -> None:
    """Remove oldest cache entries if cache exceeds max size"""
    try:
        entries = sorted(
            CACHE_DIR.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
        )
        while len(entries) >= MAX_CACHE_ENTRIES:
            oldest = entries.pop(0)
            oldest.unlink(missing_ok=True)
            logger.debug("Pruned old cache entry: %s", oldest.name)
    except OSError:
        pass


def clear_search_cache() -> int:
    """Clear all search cache entries.

    Returns:
        Number of entries removed

    """
    if not CACHE_DIR.exists():
        return 0

    count = 0
    for f in CACHE_DIR.glob("*.json"):
        f.unlink(missing_ok=True)
        count += 1

    logger.info("Cleared %d search cache entries", count)
    return count


def get_cache_stats() -> dict:
    """Get search cache statistics.

    Returns:
        Dict with cache statistics

    """
    if not CACHE_DIR.exists():
        return {"entries": 0, "total_size_bytes": 0}

    entries = 0
    total_size = 0
    for f in CACHE_DIR.glob("*.json"):
        entries += 1
        total_size += f.stat().st_size

    return {
        "entries": entries,
        "total_size_bytes": total_size,
        "max_entries": MAX_CACHE_ENTRIES,
        "ttl_hours": CACHE_TTL_HOURS,
    }
