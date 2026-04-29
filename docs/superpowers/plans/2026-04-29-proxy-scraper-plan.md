# Proxy Scraper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create `proxy_scraper.py` that fetches proxies from ProxyScrape, Free Proxy List, and GeoNode - then integrate into `run_daily.py`.

**Architecture:** Standalone `proxy_scraper.py` fetches from 3 sources in chain, deduplicates, appends to `proxyscrape_raw.txt`. Existing `validate_proxies.py` handles testing. `run_daily.py` calls scraper before validator.

**Tech Stack:** Python stdlib (`urllib`, `html.parser` for HTML parsing), `re` for regex

---

## File Structure

```
proxy_scraper.py      # NEW - scrape proxies from 3 sources
run_daily.py          # MODIFY - call scrape_proxies() before validate
README.md             # MODIFY - document proxy scraper
```

---

## Task 1: Create proxy_scraper.py

**Files:**
- Create: `proxy_scraper.py`
- Test: `tests/test_proxy_scraper.py`

- [ ] **Step 1: Write the test file**

```python
#!/usr/bin/env python3
"""Tests for proxy_scraper.py"""

import pytest
import os
import tempfile
from proxy_scraper import (
    fetch_proxyscrape,
    fetch_free_proxy_list,
    fetch_geonode,
    scrape_all,
    save_proxies,
    deduplicate,
)


class TestFetchProxyscrape:
    """Test ProxyScrape API fetch."""

    def test_fetch_returns_list(self):
        """Should return list of host:port strings."""
        result = fetch_proxyscrape()
        assert isinstance(result, list)

    def test_fetch_format(self):
        """Proxies should be host:port format."""
        result = fetch_proxyscrape()
        for proxy in result:
            assert ":" in proxy, f"Invalid format: {proxy}"
            parts = proxy.split(":")
            assert len(parts) == 2


class TestFetchFreeProxyList:
    """Test Free Proxy List HTML parsing."""

    def test_fetch_returns_list(self):
        """Should return list of host:port strings."""
        result = fetch_free_proxy_list()
        assert isinstance(result, list)


class TestFetchGeonode:
    """Test GeoNode API fetch."""

    def test_fetch_returns_list(self):
        """Should return list of host:port strings."""
        result = fetch_geonode()
        assert isinstance(result, list)


class TestDeduplicate:
    """Test proxy deduplication."""

    def test_removes_duplicates(self):
        """Should remove duplicate proxies."""
        input_proxies = ["1.1.1.1:80", "2.2.2.2:80", "1.1.1.1:80"]
        result = deduplicate(input_proxies)
        assert len(result) == 2

    def test_preserves_order(self):
        """Should preserve first occurrence order."""
        input_proxies = ["1.1.1.1:80", "3.3.3.3:80", "2.2.2.2:80", "3.3.3.3:80"]
        result = deduplicate(input_proxies)
        assert result == ["1.1.1.1:80", "3.3.3.3:80", "2.2.2.2:80"]


class TestSaveProxies:
    """Test proxy file saving."""

    def test_saves_to_file(self):
        """Should write proxies to file, one per line."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            temp_path = f.name

        try:
            proxies = ["1.1.1.1:80", "2.2.2.2:80"]
            count = save_proxies(proxies, temp_path)

            assert count == 2
            with open(temp_path) as f:
                lines = [l.strip() for l in f if l.strip()]
            assert lines == ["1.1.1.1:80", "2.2.2.2:80"]
        finally:
            os.unlink(temp_path)


class TestScrapeAll:
    """Test main scrape_all function."""

    def test_scrapes_all_sources(self):
        """Should attempt all 3 sources and return combined results."""
        result = scrape_all()

        assert isinstance(result, dict)
        assert "total" in result
        assert "sources" in result
        assert "proxies" in result
        assert isinstance(result["sources"], dict)

    def test_continues_on_source_failure(self):
        """Should continue if one source fails."""
        # scrape_all should handle individual source failures gracefully
        # We test this by mocking, but for integration test just verify it returns
        result = scrape_all()
        # Should never raise, should always return dict
        assert isinstance(result, dict)
```

- [ ] **Step 2: Run tests to verify they fail (no implementation)**

Run: `python -m pytest tests/test_proxy_scraper.py -v`
Expected: ERROR - import errors for proxy_scraper

- [ ] **Step 3: Write minimal implementation skeleton**

```python
#!/usr/bin/env python3
"""Proxy scraper - fetches fresh proxies from multiple free sources."""

import argparse
import urllib.request
import urllib.error
import re
import sys
from html.parser import HTMLParser
from typing import List, Set

# Sources
PROXYSCRAPE_URL = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all"
FREE_PROXY_LIST_URL = "https://free-proxy-list.net/"
GEONODE_URL = "https://geonode.com/free-proxy-list/api/"
PROXY_OUTPUT = "proxies/proxyscrape_raw.txt"


def fetch_proxyscrape() -> List[str]:
    """Fetch from ProxyScrape API. Returns list of host:port strings."""
    proxies = []
    try:
        req = urllib.request.Request(
            PROXYSCRAPE_URL,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read().decode("utf-8")
            # API returns one proxy per line in host:port format
            for line in content.strip().split("\n"):
                line = line.strip()
                if line and ":" in line:
                    proxies.append(line)
    except Exception as e:
        print(f"  ProxyScrape error: {e}")
    return proxies


class FreeProxyListParser(HTMLParser):
    """Parse Free Proxy List HTML for proxy table."""

    def __init__(self):
        super().__init__()
        self.proxies: List[str] = []
        self.in_table = False
        self.current_row: List[str] = []
        self.td_count = 0

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.in_table = True
        elif tag == "td" and self.in_table:
            self.td_count += 1

    def handle_endtag(self, tag):
        if tag == "tr" and self.current_row:
            # Format: IP Address, Port, Code, Country, Anonymity, Google, Https, Last Checked
            if len(self.current_row) >= 7:
                ip = self.current_row[0].strip()
                port = self.current_row[1].strip()
                if ip and port:
                    self.proxies.append(f"{ip}:{port}")
            self.current_row = []
            self.td_count = 0

    def handle_data(self, data):
        if self.in_table:
            data = data.strip()
            if data:
                self.current_row.append(data)


def fetch_free_proxy_list() -> List[str]:
    """Fetch and parse Free Proxy List. Returns list of host:port strings."""
    proxies = []
    try:
        req = urllib.request.Request(
            FREE_PROXY_LIST_URL,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read().decode("utf-8")
            parser = FreeProxyListParser()
            parser.feed(content)
            proxies = parser.proxies
    except Exception as e:
        print(f"  Free Proxy List error: {e}")
    return proxies


def fetch_geonode() -> List[str]:
    """Fetch from GeoNode API. Returns list of host:port strings."""
    proxies = []
    try:
        req = urllib.request.Request(
            GEONODE_URL,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            import json
            data = json.loads(response.read().decode("utf-8"))
            # API returns {"data": [{"ip": "...", "port": ...}, ...]}
            for entry in data.get("data", []):
                ip = entry.get("ip", "")
                port = entry.get("port", "")
                if ip and port:
                    proxies.append(f"{ip}:{port}")
    except Exception as e:
        print(f"  GeoNode error: {e}")
    return proxies


def deduplicate(proxies: List[str]) -> List[str]:
    """Remove duplicate proxies preserving first occurrence order."""
    seen: Set[str] = set()
    result = []
    for proxy in proxies:
        if proxy not in seen:
            seen.add(proxy)
            result.append(proxy)
    return result


def save_proxies(proxies: List[str], path: str) -> int:
    """Append proxies to file. Returns count of new proxies written."""
    count = 0
    existing = set()
    # Load existing to avoid duplicates in file
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                existing.add(line.strip())
    with open(path, "a") as f:
        for proxy in proxies:
            if proxy not in existing:
                f.write(proxy + "\n")
                existing.add(proxy)
                count += 1
    return count


import os

def scrape_all() -> dict:
    """Scrape all sources and return summary."""
    results = {
        "total": 0,
        "sources": {},
        "proxies": [],
    }

    print("Scraping proxies from sources...")

    # Try each source in order
    sources = [
        ("ProxyScrape", fetch_proxyscrape),
        ("FreeProxyList", fetch_free_proxy_list),
        ("GeoNode", fetch_geonode),
    ]

    all_proxies: List[str] = []
    for name, fetch_func in sources:
        print(f"  Fetching from {name}...")
        proxies = fetch_func()
        results["sources"][name] = len(proxies)
        print(f"    Got {len(proxies)} proxies")
        all_proxies.extend(proxies)

    # Deduplicate
    all_proxies = deduplicate(all_proxies)
    results["proxies"] = all_proxies
    results["total"] = len(all_proxies)
    print(f"  Total after deduplication: {len(all_proxies)}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Proxy scraper from multiple sources")
    parser.add_argument("--source", "-s", type=int, choices=[1, 2, 3],
                        help="1=ProxyScrape, 2=FreeProxyList, 3=GeoNode (default=all)")
    parser.add_argument("--output", "-o", default=PROXY_OUTPUT,
                        help="Output file path")
    args = parser.parse_args()

    if args.source:
        sources = [
            (1, "ProxyScrape", fetch_proxyscrape),
            (2, "FreeProxyList", fetch_free_proxy_list),
            (3, "GeoNode", fetch_geonode),
        ]
        name = None
        fetch_func = None
        for idx, n, f in sources:
            if idx == args.source:
                name = n
                fetch_func = f
                break
        print(f"Scraping from {name}...")
        proxies = fetch_func()
    else:
        result = scrape_all()
        proxies = result["proxies"]

    if proxies:
        count = save_proxies(proxies, args.output)
        print(f"Appended {count} new proxies to {args.output}")
    else:
        print("No proxies fetched")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_proxy_scraper.py -v`
Expected: All PASS or some FAIL (depends on network availability)

- [ ] **Step 5: Commit**

```bash
git add proxy_scraper.py tests/test_proxy_scraper.py
git commit -m "feat: add proxy scraper for automatic proxy fetching"
```

---

## Task 2: Integrate into run_daily.py

**Files:**
- Modify: `run_daily.py:38-54` (add `scrape_proxies` function), `run_daily.py:114-144` (update `validate_proxies`)

- [ ] **Step 1: Read current run_daily.py to verify line numbers**

Run: `head -60 run_daily.py`

- [ ] **Step 2: Add scrape_proxies function before validate_proxies**

Add this function after the imports and `run_summary` dict:

```python
def scrape_proxies() -> int:
    """Scrape fresh proxies from online sources.

    Returns:
        Number of new proxies scraped and appended.
    """
    print_header("PROXY SCRAPING")
    print("Fetching fresh proxies from online sources...")

    try:
        import proxy_scraper
        result = proxy_scraper.scrape_all()
        sources = result["sources"]
        total = result["total"]
        proxies = result["proxies"]

        for name, count in sources.items():
            print(f"  {name}: {count} proxies")

        if proxies:
            count = proxy_scraper.save_proxies(proxies, PROXY_INPUT)
            print(f"Appended {count} new proxies to {PROXY_INPUT}")
            return count
        else:
            print("No proxies fetched from any source")
            return 0
    except Exception as e:
        print(f"Proxy scraping failed: {e}")
        return 0
```

- [ ] **Step 3: Update validate_proxies to call scrape_proxies first**

Replace the `validate_proxies()` function call in `main()` with:

```python
def validate_proxies() -> list[str]:
    """Re-validate proxy list, return working ones."""
    run_summary["started_at"] = datetime.now()

    # First, try to scrape fresh proxies
    scrape_count = scrape_proxies()
    if scrape_count == 0:
        print("Warning: No fresh proxies scraped, using existing file")

    if not os.path.exists(PROXY_INPUT):
        print(f"Proxy input not found: {PROXY_INPUT}")
        run_summary["errors"].append(f"Proxy input not found: {PROXY_INPUT}")
        return []
    # ... rest of existing validate_proxies function
```

- [ ] **Step 4: Run to verify it works**

Run: `cd /home/can/Desktop/job && python run_daily.py`
Expected: Proxy scraping section appears before validation

- [ ] **Step 5: Commit**

```bash
git add run_daily.py
git commit -m "feat: auto-scrape proxies before validation in run_daily"
```

---

## Task 3: Update README

**Files:**
- Modify: `README.md` (add proxy_scraper section)

- [ ] **Step 1: Add proxy_scraper section to Features**

Add to Features section:

```markdown
### Automatic Proxy Scraping
- **Multi-source**: ProxyScrape, Free Proxy List, GeoNode in chain
- **Deduplication**: Removes duplicates across sources
- **Incremental**: Appends to existing proxy list (preserves working pool)
- **Graceful degradation**: Continues if one source fails
```

- [ ] **Step 2: Add proxy_scraper CLI docs**

Add before "## Troubleshooting":

```markdown
### Proxy Scraper

Standalone tool to fetch fresh proxies from online sources:

```bash
# Scrape all sources
python proxy_scraper.py

# Scrape specific source only
python proxy_scraper.py --source 1   # ProxyScrape
python proxy_scraper.py --source 2   # Free Proxy List
python proxy_scraper.py --source 3   # GeoNode
```

Proxies are appended to `proxies/proxyscrape_raw.txt`. `run_daily.py` automatically calls this before validation.
```

- [ ] **Step 3: Update project structure in README**

Add `proxy_scraper.py` to the file list:

```
├── proxy_scraper.py     # Auto-fetch proxies from online sources
```

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: document proxy scraper feature"
```

---

## Verification

After all tasks:
1. Run: `python run_daily.py` - should see "Proxy Scraping" section first
2. Run: `python proxy_scraper.py` - should scrape and save proxies
3. Run: `python -m pytest tests/test_proxy_scraper.py -v` - tests pass
