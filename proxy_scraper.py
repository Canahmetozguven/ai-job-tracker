#!/usr/bin/env python3
"""Fetch and persist free proxy lists from multiple public sources."""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

PROXYSCRAPE_URL = (
    "https://api.proxyscrape.com/v2/?request=displayproxies"
    "&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all"
)
FREE_PROXY_LIST_URL = "https://free-proxy-list.net/"
GEONODE_URL = "https://geonode.com/free-proxy-list/api/"
DEFAULT_OUTPUT_PATH = "proxies/proxyscrape_raw.txt"
USER_AGENT = "Mozilla/5.0"

_PROXY_RE = re.compile(r"^(?P<host>[^\s:/]+):(?P<port>\d{1,5})$")


def _normalize_proxy(value: str | None) -> str | None:
    """Normalize a proxy string to ``host:port`` if possible."""

    if not value:
        return None

    cleaned = value.strip()
    if not cleaned:
        return None

    if "://" in cleaned:
        cleaned = cleaned.split("://", 1)[1]

    cleaned = cleaned.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
    match = _PROXY_RE.match(cleaned)
    if not match:
        return None

    port = int(match.group("port"))
    if not 1 <= port <= 65535:
        return None

    return f"{match.group('host')}:{port}"


def _build_request(url: str) -> urllib.request.Request:
    return urllib.request.Request(url, headers={"User-Agent": USER_AGENT})


def _fetch_text(url: str, timeout: int = 15) -> str:
    with urllib.request.urlopen(_build_request(url), timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_proxyscrape() -> list[str]:
    """Fetch proxies from ProxyScrape's line-based API."""

    try:
        body = _fetch_text(PROXYSCRAPE_URL)
        proxies: list[str] = []
        for line in body.splitlines():
            proxy = _normalize_proxy(line)
            if proxy:
                proxies.append(proxy)
        return proxies
    except Exception:
        return []


class _FreeProxyListParser(HTMLParser):
    """Extract proxy rows from the free-proxy-list table."""

    def __init__(self) -> None:
        super().__init__()
        self._in_target_table = False
        self._in_row = False
        self._current_cell: list[str] | None = None
        self._current_row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {name: value for name, value in attrs}
        if tag == "table" and attr_map.get("id") == "proxylisttable":
            self._in_target_table = True
            return

        if not self._in_target_table:
            return

        if tag == "tr":
            self._in_row = True
            self._current_row = []
        elif tag in {"td", "th"} and self._in_row:
            self._current_cell = []

    def handle_data(self, data: str) -> None:
        if self._current_cell is not None:
            self._current_cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "table" and self._in_target_table:
            self._in_target_table = False
            self._in_row = False
            self._current_cell = None
            return

        if not self._in_target_table:
            return

        if tag in {"td", "th"} and self._current_cell is not None:
            cell_text = "".join(self._current_cell).strip()
            self._current_row.append(cell_text)
            self._current_cell = None
        elif tag == "tr" and self._in_row:
            if self._current_row:
                self.rows.append(self._current_row)
            self._current_row = []
            self._in_row = False


def fetch_free_proxy_list() -> list[str]:
    """Fetch proxies from the HTML table at free-proxy-list.net."""

    try:
        html = _fetch_text(FREE_PROXY_LIST_URL)
        parser = _FreeProxyListParser()
        parser.feed(html)

        proxies: list[str] = []
        for row in parser.rows:
            if len(row) < 2:
                continue
            proxy = _normalize_proxy(f"{row[0]}:{row[1]}")
            if proxy:
                proxies.append(proxy)
        return proxies
    except Exception:
        return []


def _extract_geonode_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if isinstance(payload, dict):
        for key in ("data", "results", "proxies", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]

    return []


def fetch_geonode() -> list[str]:
    """Fetch proxies from GeoNode's JSON API."""

    try:
        raw = _fetch_text(GEONODE_URL)
        payload = json.loads(raw)
        proxies: list[str] = []
        for item in _extract_geonode_items(payload):
            if "proxy" in item:
                proxy = _normalize_proxy(str(item.get("proxy")))
            else:
                host = item.get("ip") or item.get("ipAddress") or item.get("host")
                port = item.get("port") or item.get("proxyPort") or item.get("port_number")
                proxy = _normalize_proxy(f"{host}:{port}") if host and port else None
            if proxy:
                proxies.append(proxy)
        return proxies
    except Exception:
        return []


def deduplicate(proxies: list[str]) -> list[str]:
    """Normalize and deduplicate proxies while preserving order."""

    seen: set[str] = set()
    result: list[str] = []
    for proxy in proxies:
        normalized = _normalize_proxy(proxy)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def save_proxies(proxies: list[str], path: str) -> int:
    """Append new unique proxies to ``path`` and return the count written."""

    try:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)

        existing: set[str] = set()
        if output.exists():
            try:
                existing = {
                    proxy
                    for proxy in (_normalize_proxy(line) for line in output.read_text().splitlines())
                    if proxy
                }
            except Exception:
                existing = set()

        written = 0
        new_proxies = deduplicate(proxies)
        with output.open("a", encoding="utf-8") as handle:
            for proxy in new_proxies:
                if proxy in existing:
                    continue
                handle.write(proxy + "\n")
                existing.add(proxy)
                written += 1
        return written
    except Exception:
        return 0


def scrape_all(output_path: str | None = None) -> dict[str, Any]:
    """Fetch all sources, deduplicate, save, and return a summary."""

    target_path = output_path or DEFAULT_OUTPUT_PATH
    sources = {
        "proxyscrape": fetch_proxyscrape(),
        "free_proxy_list": fetch_free_proxy_list(),
        "geonode": fetch_geonode(),
    }
    proxies = deduplicate(
        sources["proxyscrape"] + sources["free_proxy_list"] + sources["geonode"]
    )
    save_proxies(proxies, target_path)
    return {"total": len(proxies), "sources": sources, "proxies": proxies}


def _scrape_single_source(source: int, output_path: str) -> dict[str, Any]:
    mapping = {
        1: ("proxyscrape", fetch_proxyscrape),
        2: ("free_proxy_list", fetch_free_proxy_list),
        3: ("geonode", fetch_geonode),
    }
    source_name, fetcher = mapping[source]
    proxies = deduplicate(fetcher())
    save_proxies(proxies, output_path)
    return {"total": len(proxies), "sources": {source_name: proxies}, "proxies": proxies}


def main(argv: list[str] | None = None) -> dict[str, Any]:
    """CLI entry point for fetching proxies."""

    parser = argparse.ArgumentParser(description="Fetch free proxies from public sources")
    parser.add_argument(
        "--source",
        type=int,
        choices=[1, 2, 3],
        help="Fetch only one source: 1=ProxyScrape, 2=Free Proxy List, 3=GeoNode",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_PATH,
        help=f"Output path (default: {DEFAULT_OUTPUT_PATH})",
    )

    args = parser.parse_args(argv)

    if args.source:
        result = _scrape_single_source(args.source, args.output)
        source_name = next(iter(result["sources"]))
        print(f"Fetched {result['total']} proxies from {source_name}")
    else:
        result = scrape_all(output_path=args.output)
        print(
            f"Fetched {result['total']} unique proxies from {len(result['sources'])} sources"
        )

    print(f"Saved to {args.output}")
    return result


if __name__ == "__main__":
    main()
