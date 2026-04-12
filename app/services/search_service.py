# app/services/search_service.py
"""
Torrent search service — async parallel search across public torrent APIs
with YAML config-driven parsing into a unified schema.

Adapted from /infra/experiments/tse (tse.py + config_parse.py).
"""

import asyncio
import logging
import re
from pathlib import Path

import httpx
import yaml

logger = logging.getLogger("rear-differential.search")

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)
TIMEOUT = 15.0
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


# ---------------------------------------------------------------------------
# YAML config-driven parser
# ---------------------------------------------------------------------------

def _load_config(source_name: str) -> dict:
    path = CONFIG_DIR / f"{source_name}.yaml"
    with open(path) as f:
        return yaml.safe_load(f)


def _resolve_path(obj, path: str):
    if path == ".":
        return obj
    for key in path.split("."):
        if isinstance(obj, dict):
            obj = obj.get(key)
        else:
            return None
    return obj


def _lookup(record: dict, ref: str, parent: dict = None):
    if ref.startswith("parent.") and parent is not None:
        return _resolve_path(parent, ref[len("parent."):])
    if ref.startswith("child.") and isinstance(record, dict):
        return _resolve_path(record, ref[len("child."):])
    if isinstance(record, dict):
        return _resolve_path(record, ref)
    return None


def _resolve_field(record, field_spec: str, parent: dict = None):
    if field_spec is None or field_spec == "null":
        return None

    # template: magnet:?xt=urn:btih:{hash}&dn={name}
    if isinstance(field_spec, str) and field_spec.startswith("template:"):
        import urllib.parse
        template = field_spec[len("template:"):]
        def _replace(match):
            ref = match.group(1)
            val = _lookup(record, ref, parent)
            if val is None:
                return ""
            return urllib.parse.quote(str(val), safe="")
        return re.sub(r'\{([^}]+)\}', _replace, template)

    # regex:field:pattern
    if isinstance(field_spec, str) and field_spec.startswith("regex:"):
        parts = field_spec[len("regex:"):].split(":", 1)
        if len(parts) != 2:
            return None
        field_name, pattern = parts
        raw_val = _lookup(record, field_name, parent)
        if raw_val is None:
            return None
        m = re.search(pattern, str(raw_val), re.IGNORECASE)
        if m and m.group(1):
            val = m.group(1)
            if val.isdigit():
                return int(val)
            return val
        return None

    # direct field lookup
    return _lookup(record, field_spec, parent)


def _parse_source(source_name: str, raw_data) -> list[dict]:
    """Parse raw API JSON using the YAML config for this source."""
    config = _load_config(source_name)
    field_map = config["fields"]

    items = _resolve_path(raw_data, config["items_path"])
    if not items:
        return []

    # apply filter if defined
    filt = config.get("filter")
    if filt:
        field = filt["field"]
        not_eq = filt.get("not_equals")
        if not_eq is not None:
            items = [i for i in items if str(i.get(field)) != str(not_eq)]

    results = []
    children_path = config.get("children_path")

    if children_path:
        for parent_item in items:
            children = parent_item.get(children_path) or []
            for child in children:
                record = {}
                for out_field, spec in field_map.items():
                    record[out_field] = _resolve_field(child, spec, parent=parent_item)
                record["source"] = source_name
                results.append(record)
    else:
        for item in items:
            record = {}
            for out_field, spec in field_map.items():
                record[out_field] = _resolve_field(item, spec)
            record["source"] = source_name
            results.append(record)

    return results


# ---------------------------------------------------------------------------
# Async search functions (one per source)
# ---------------------------------------------------------------------------

async def _search_yts(client: httpx.AsyncClient, query: str) -> dict:
    """YTS movies API."""
    url = "https://movies-api.accel.li/api/v2/list_movies.json"
    resp = await client.get(url, params={"query_term": query, "limit": 50})
    resp.raise_for_status()
    return {"source": "yts", "raw_data": resp.json()}


async def _search_tpb(client: httpx.AsyncClient, query: str) -> dict:
    """The Pirate Bay API."""
    url = "https://apibay.org/q.php"
    resp = await client.get(url, params={"q": query})
    resp.raise_for_status()
    data = resp.json()
    # TPB returns a single-element list with id "0" for no results
    if isinstance(data, list) and len(data) == 1 and data[0].get("id") == "0":
        data = []
    return {"source": "tpb", "raw_data": data}


async def _search_eztv(client: httpx.AsyncClient, query: str) -> dict:
    """EZTV TV API — fetches recent torrents and filters by query text."""
    url = "https://eztvx.to/api/get-torrents"
    resp = await client.get(url, params={"limit": 100, "page": 1})
    resp.raise_for_status()
    data = resp.json()
    # EZTV API doesn't support text search; filter client-side
    torrents = data.get("torrents") or []
    q_lower = query.lower()
    matched = [t for t in torrents if q_lower in t.get("title", "").lower()]
    filtered = dict(data)
    filtered["torrents"] = matched
    return {"source": "eztv", "raw_data": filtered}


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

_SOURCES = [
    ("yts", _search_yts),
    ("tpb", _search_tpb),
    ("eztv", _search_eztv),
]


class SearchService:
    """Searches public torrent APIs and returns parsed results."""

    async def search(self, query: str) -> list[dict]:
        """
        Search for torrents matching query across all sources.

        Args:
            query: text search string

        Returns:
            list of unified torrent result dicts
        """
        sources = _SOURCES

        async with httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
            follow_redirects=True,
        ) as client:
            tasks = [fn(client, query) for _, fn in sources]
            raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        all_parsed = []
        for i, result in enumerate(raw_results):
            source_name = sources[i][0]
            if isinstance(result, Exception):
                logger.warning(f"Search failed for {source_name}: {result}")
                continue
            try:
                parsed = _parse_source(source_name, result["raw_data"])
                all_parsed.extend(parsed)
            except Exception as e:
                logger.warning(f"Parse failed for {source_name}: {e}")

        # Deduplicate by magnet_link — keeps first occurrence
        seen = set()
        deduped = []
        for item in all_parsed:
            magnet = item.get("magnet_link")
            if magnet and magnet in seen:
                continue
            if magnet:
                seen.add(magnet)
            deduped.append(item)

        return deduped
