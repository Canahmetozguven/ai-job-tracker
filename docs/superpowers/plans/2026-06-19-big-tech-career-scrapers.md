# Big Tech Career Sites Scraper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a third cron pass that scrapes each of the Big Tech 7 (Apple, Microsoft, Google, Amazon, Meta, Nvidia, Tesla) directly from their own career sites, producing records tagged `source_pass="career_site"` with a per-company `source_company` field. Merges into the existing `jobs_linkedin.jsonl` alongside the Turkey-local and Big-Tech-via-LinkedIn records.

**Architecture:** New `career_scrapers/` Python package with a `BaseCareerScraper` abstract class and one concrete scraper per company. A new top-level `career_scraper.py` CLI loads the registry, invokes each scraper in isolation (per-scraper failures don't abort), aggregates results, dedupes by `job_url`, and appends to the JSONL. `run_daily.py` gets a third invocation; `telegram_notify.py` gets a third summary row.

**Tech Stack:** Python 3, `urllib.request` (stdlib — no new deps), `pytest`, existing `telegram-bot`.

**Spec:** `docs/superpowers/specs/2026-06-19-big-tech-career-scrapers-design.md`

**Endpoint-discovery research notes (from plan-time recon):**
- ✅ **Amazon** — `https://amazon.jobs/en/search.json` returns real-time JSON, no auth, works for any query.
- ❌ **Google** — `careers.google.com/api/v3/search/` returns 404. Need browser-devtools network-tab research. Likely GraphQL or POST-required.
- ⚠️ **Meta** — `metacareers.com/graphql` returns 200 with HTML body, indicating the endpoint exists but requires proper CSRF/cookies and probably GraphQL POST.
- ⚠️ **Microsoft** — `careers.microsoft.com/api/v1/roles` returns HTML page. Need to inspect their SPA's network calls.
- ❌ **Apple** — `jobs.apple.com/api/v1/jobListings` returns 401 (endpoint exists, needs auth). Their search page may need browser scraping.
- ⚠️ **Nvidia** — Workday (`nvidia.wd5.myworkdayjobs.com`). Workday is a known difficult target requiring a session-establishment POST flow.
- ❌ **Tesla** — `tesla.com/careers/api/jobs` returns 403. Endpoint exists but is blocked. Likely needs headers/cookies.

The plan treats these in 3 tiers: **tier-1 confirmed (Amazon)**, **tier-2 research-likely (Google, Meta, Microsoft)**, **tier-3 experimental (Apple, Nvidia, Tesla)**. Per-scraper failure is acceptable; the framework logs and skips.

---

## File Structure

**Create:**
- `career_scrapers/__init__.py` — registry (`SCRAPERS: dict[str, type[BaseCareerScraper]]`) + module imports
- `career_scrapers/base.py` — `BaseCareerScraper` abstract class
- `career_scrapers/amazon.py` — `AmazonScraper` (tier-1)
- `career_scrapers/google.py` — `GoogleScraper` (tier-2)
- `career_scrapers/meta.py` — `MetaScraper` (tier-2)
- `career_scrapers/microsoft.py` — `MicrosoftScraper` (tier-2)
- `career_scrapers/apple.py` — `AppleScraper` (tier-3)
- `career_scrapers/nvidia.py` — `NvidiaScraper` (tier-3, Workday)
- `career_scrapers/tesla.py` — `TeslaScraper` (tier-3)
- `career_scraper.py` — top-level CLI
- `tests/test_career_scrapers.py` — base + per-company tests
- `tests/test_career_scraper_cli.py` — CLI tests
- `tests/fixtures/career_sites/amazon.json` — sample Amazon response

**Modify:**
- `run_daily.py` — add `career_site` bucket to `run_summary["scrape"]`, add 3rd pass invocation, update exit-condition
- `telegram_notify.py` — add `"career_site": "🏢 Career sites"` label, add per-pass test
- `tests/test_analyzer.py` — add 3-pass formatter test

---

## Task 1: Create `career_scrapers/` package skeleton with `BaseCareerScraper`

**Files:**
- Create: `career_scrapers/__init__.py`
- Create: `career_scrapers/base.py`
- Test: `tests/test_career_scrapers.py`

- [ ] **Step 1: Create empty `career_scrapers/__init__.py`**

```python
"""Big Tech 7 career-site scrapers.

Each module registers a concrete scraper class by importing it in
`__all__` below; the SCRAPERS dict is auto-populated.
"""
from career_scrapers.base import BaseCareerScraper

# Concrete scrapers (added in later tasks)
from career_scrapers.amazon import AmazonScraper

SCRAPERS: dict[str, type[BaseCareerScraper]] = {
    cls.name: cls
    for cls in [AmazonScraper]
}

__all__ = ["BaseCareerScraper", "SCRAPERS"]
```

- [ ] **Step 2: Create `career_scrapers/base.py` with `BaseCareerScraper`**

```python
"""Abstract base for Big Tech career-site scrapers."""

from __future__ import annotations

import time
import urllib.error
import urllib.request
from typing import Any, ClassVar


class BaseCareerScraper:
    """Abstract base for one company's career-site scraper.

    Subclasses must set `name` and `base_url` as class vars, and override
    `fetch_jobs(query, limit) -> list[dict]`. The framework provides throttling,
    retry, and a record-builder helper that fills `source_pass` and
    `source_company` automatically.
    """

    name: ClassVar[str] = ""
    base_url: ClassVar[str] = ""
    rate_limit_seconds: ClassVar[float] = 1.0
    max_retries: ClassVar[int] = 3

    def __init__(self, proxy: str | None = None):
        if not self.name:
            raise ValueError(f"{type(self).__name__} must set `name` class var")
        if not self.base_url:
            raise ValueError(f"{type(self).__name__} must set `base_url` class var")
        self.proxy = proxy
        self._last_request_at: float = 0.0

    def fetch_jobs(self, query: str, limit: int = 50) -> list[dict]:
        """Override in subclass. Return records matching the common record schema."""
        raise NotImplementedError

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.rate_limit_seconds:
            time.sleep(self.rate_limit_seconds - elapsed)
        self._last_request_at = time.monotonic()

    def _get(self, url: str, *, headers: dict[str, str] | None = None) -> bytes:
        """GET with throttling, retry on 5xx/429/timeout, optional proxy.

        Raises on permanent failure (after max_retries).
        """
        self._throttle()
        merged_headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
        if headers:
            merged_headers.update(headers)
        req = urllib.request.Request(url, headers=merged_headers)
        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    return r.read()
            except urllib.error.HTTPError as e:
                # 429 / 5xx are retryable; 4xx other than 429 is not.
                if e.code in (429, 500, 502, 503, 504) and attempt < self.max_retries - 1:
                    last_exc = e
                    time.sleep(2 ** attempt)
                    continue
                raise
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                last_exc = e
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise
        # Unreachable, but make type-checkers happy.
        raise RuntimeError(f"{self.name}: _get exhausted retries: {last_exc}")

    def _make_record(
        self,
        *,
        title: str,
        company: str,
        location: str,
        job_url: str,
        description: str | None = None,
        date_posted: str | None = None,
        source: str | None = None,
        is_remote: bool | None = None,
        salary: Any = None,
    ) -> dict:
        return {
            "title": title,
            "company": company,
            "location": location,
            "job_url": job_url,
            "description": description,
            "date_posted": date_posted or "unknown",
            "job_type": None,
            "salary": salary,
            "source": source or self._source_tag(),
            "is_remote": is_remote,
            "source_pass": "career_site",
            "source_company": self.name,
        }

    def _source_tag(self) -> str:
        return f"{self.name.lower()}_career"
```

- [ ] **Step 3: Create stub `career_scrapers/amazon.py` (full impl comes in Task 2)**

The package import in Task 1's `__init__.py` references `AmazonScraper`, so we need a stub now. Task 2 will replace it.

```python
"""Amazon careers scraper (placeholder — implemented in Task 2)."""

from career_scrapers.base import BaseCareerScraper


class AmazonScraper(BaseCareerScraper):
    name = "Amazon"
    base_url = "https://amazon.jobs"

    def fetch_jobs(self, query: str, limit: int = 50) -> list[dict]:
        return []
```

- [ ] **Step 4: Create `tests/test_career_scrapers.py` with base-class tests**

```python
"""Unit tests for career_scrapers package."""

import urllib.error
from unittest.mock import patch, MagicMock

import pytest

from career_scrapers import SCRAPERS
from career_scrapers.amazon import AmazonScraper
from career_scrapers.base import BaseCareerScraper


# --- registry ---


def test_registry_contains_amazon():
    assert "Amazon" in SCRAPERS
    assert SCRAPERS["Amazon"] is AmazonScraper


# --- BaseCareerScraper init ---


def test_base_subclass_requires_name():
    class Bad(BaseCareerScraper):
        base_url = "https://example.com"

    with pytest.raises(ValueError, match="must set `name`"):
        Bad()


def test_base_subclass_requires_base_url():
    class Bad(BaseCareerScraper):
        name = "Bad"

    with pytest.raises(ValueError, match="must set `base_url`"):
        Bad()


def test_base_subclass_init_succeeds():
    s = AmazonScraper()
    assert s.name == "Amazon"
    assert s.base_url == "https://amazon.jobs"
    assert s.proxy is None


# --- _make_record ---


def test_make_record_fills_source_pass_and_company():
    s = AmazonScraper()
    rec = s._make_record(
        title="DS", company="Amazon", location="Seattle",
        job_url="https://amazon.jobs/j/123",
    )
    assert rec["source_pass"] == "career_site"
    assert rec["source_company"] == "Amazon"
    assert rec["source"] == "amazon_career"
    assert rec["title"] == "DS"
    assert rec["date_posted"] == "unknown"
    assert rec["description"] is None
    assert rec["is_remote"] is None
    assert rec["salary"] is None


def test_make_record_uses_explicit_source():
    s = AmazonScraper()
    rec = s._make_record(
        title="DS", company="Amazon", location="X",
        job_url="https://example.com/1", source="custom_tag",
    )
    assert rec["source"] == "custom_tag"


def test_make_record_preserves_explicit_date_posted():
    s = AmazonScraper()
    rec = s._make_record(
        title="DS", company="Amazon", location="X",
        job_url="https://example.com/1", date_posted="2026-01-01",
    )
    assert rec["date_posted"] == "2026-01-01"


# --- _throttle ---


def test_throttle_sleeps_to_meet_rate_limit():
    import time
    s = AmazonScraper()
    s.rate_limit_seconds = 0.1
    s._throttle()  # first call: no sleep
    t0 = time.monotonic()
    s._throttle()  # second call: should sleep ~0.1s
    elapsed = time.monotonic() - t0
    assert elapsed >= 0.09


# --- _get retry ---


def test_get_retries_on_5xx_then_succeeds():
    s = AmazonScraper()
    call_count = {"n": 0}

    def fake_urlopen(req, timeout):
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise urllib.error.HTTPError(req.full_url, 503, "Service Unavailable", {}, None)
        m = MagicMock()
        m.__enter__ = lambda self: self
        m.__exit__ = lambda self, *a: None
        m.read.return_value = b'{"ok": true}'
        return m

    with patch("career_scrapers.base.urllib.request.urlopen", side_effect=fake_urlopen):
        body = s._get("https://example.com/api")
    assert body == b'{"ok": true}'
    assert call_count["n"] == 3


def test_get_raises_after_max_retries():
    s = AmazonScraper()
    s.max_retries = 2

    def always_503(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 503, "Service Unavailable", {}, None)

    with patch("career_scrapers.base.urllib.request.urlopen", side_effect=always_503):
        with pytest.raises(urllib.error.HTTPError):
            s._get("https://example.com/api")


def test_get_does_not_retry_on_404():
    s = AmazonScraper()
    call_count = {"n": 0}

    def always_404(req, timeout):
        call_count["n"] += 1
        raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)

    with patch("career_scrapers.base.urllib.request.urlopen", side_effect=always_404):
        with pytest.raises(urllib.error.HTTPError):
            s._get("https://example.com/api")
    assert call_count["n"] == 1  # no retry
```

- [ ] **Step 5: Run tests, verify pass**

Run: `PYTHONPATH=. /home/can/Desktop/job/.venv/bin/pytest tests/test_career_scrapers.py -v`
Expected: PASS — 11 tests passing.

- [ ] **Step 6: Commit**

```bash
git add career_scrapers/__init__.py career_scrapers/base.py career_scrapers/amazon.py tests/test_career_scrapers.py
git commit -m "feat(career_scrapers): add BaseCareerScraper + package skeleton"
```

---

## Task 2: Implement `AmazonScraper` (tier-1, confirmed working API)

**Files:**
- Modify: `career_scrapers/amazon.py`
- Create: `tests/fixtures/career_sites/amazon.json`
- Test: `tests/test_career_scrapers.py` (append Amazon-specific test)

- [ ] **Step 1: Save a real Amazon response as a test fixture**

Run this once to capture a real response, then save it as the fixture:

```bash
PYTHONPATH=. /home/can/Desktop/job/.venv/bin/python -c "
import urllib.request, json
req = urllib.request.Request(
    'https://amazon.jobs/en/search.json?result_limit=2&category=Data+Science&loc_query=',
    headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'},
)
print(json.dumps(json.loads(urllib.request.urlopen(req, timeout=15).read()), indent=2))
" > tests/fixtures/career_sites/amazon.json
```

If the above command produces a non-JSON error page (Amazon sometimes blocks scripted requests), manually fetch the URL in a browser, save the response as `tests/fixtures/career_sites/amazon.json`.

- [ ] **Step 2: Inspect the fixture and identify the JSON fields**

Open `tests/fixtures/career_sites/amazon.json` and note the shape. Amazon's `/en/search.json` returns:

```json
{
  "total_hits": <int>,
  "jobs": [
    {
      "title": "Data Scientist",
      "company_name": "Amazon.com Services LLC",
      "location": "US, WA, Seattle",
      "url": "https://www.amazon.jobs/en/jobs/12345/data-scientist",
      "description": "...",
      "posted_date": "2026-06-15"
    }
  ]
}
```

(If the actual shape differs, adjust the field names in step 3 accordingly.)

- [ ] **Step 3: Replace `career_scrapers/amazon.py` with the real implementation**

```python
"""Amazon careers scraper.

Uses the public JSON API at https://amazon.jobs/en/search.json.
No auth required; throttled to 1.0s between requests.
"""

import json

from career_scrapers.base import BaseCareerScraper


class AmazonScraper(BaseCareerScraper):
    name = "Amazon"
    base_url = "https://amazon.jobs"
    rate_limit_seconds = 1.0

    SEARCH_URL = "https://amazon.jobs/en/search.json"

    def fetch_jobs(self, query: str, limit: int = 50) -> list[dict]:
        url = f"{self.SEARCH_URL}?result_limit={limit}&keywords={query}"
        body = self._get(url)
        data = json.loads(body)
        records = []
        for job in data.get("jobs", []):
            records.append(self._make_record(
                title=job.get("title", ""),
                company=self.name,                                # canonical, not Amazon's "Amazon.com Services LLC"
                location=job.get("location", ""),
                job_url=job.get("url", ""),
                description=job.get("description"),
                date_posted=job.get("posted_date"),
            ))
        return records
```

- [ ] **Step 4: Add a happy-path test using the fixture**

Append to `tests/test_career_scrapers.py`:

```python
# --- AmazonScraper ---


def test_amazon_scraper_parses_fixture():
    from pathlib import Path
    import json as _json
    fixture = Path(__file__).parent / "fixtures" / "career_sites" / "amazon.json"
    fake_body = fixture.read_bytes()

    s = AmazonScraper()
    with patch("career_scrapers.amazon.BaseCareerScraper._get", return_value=fake_body):
        records = s.fetch_jobs("data scientist", limit=10)
    assert isinstance(records, list)
    for r in records:
        assert r["source_pass"] == "career_site"
        assert r["source_company"] == "Amazon"
        assert r["source"] == "amazon_career"
        assert r["company"] == "Amazon"
        assert r["job_url"].startswith("https://")
    # If the fixture has at least one job, verify it parsed.
    data = _json.loads(fake_body)
    if data.get("jobs"):
        assert len(records) == len(data["jobs"])
        first = records[0]
        assert first["title"] == data["jobs"][0]["title"]


def test_amazon_scraper_returns_empty_on_no_jobs():
    s = AmazonScraper()
    empty = b'{"total_hits": 0, "jobs": []}'
    with patch("career_scrapers.amazon.BaseCareerScraper._get", return_value=empty):
        assert s.fetch_jobs("x") == []
```

- [ ] **Step 5: Run tests**

Run: `PYTHONPATH=. /home/can/Desktop/job/.venv/bin/pytest tests/test_career_scrapers.py -v`
Expected: PASS — 13 tests (11 base + 2 Amazon).

- [ ] **Step 6: Commit**

```bash
git add career_scrapers/amazon.py tests/fixtures/career_sites/amazon.json tests/test_career_scrapers.py
git commit -m "feat(career_scrapers): implement AmazonScraper (tier-1, public API)"
```

---

## Task 3: Create `career_scraper.py` top-level CLI

**Files:**
- Create: `career_scraper.py`
- Test: `tests/test_career_scraper_cli.py`

- [ ] **Step 1: Create `tests/test_career_scraper_cli.py` with failing tests**

```python
"""Tests for career_scraper.py CLI (orchestrator)."""

import json
import sys
from unittest.mock import patch

import pytest

import career_scraper as cs


def _write_jsonl(path, records):
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def test_cli_help_shows_expected_flags(capsys):
    with pytest.raises(SystemExit) as exc:
        cs.main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    for flag in ["--query", "--limit", "--proxy", "--output", "--append"]:
        assert flag in out


def test_cli_invokes_each_registered_scraper(tmp_path):
    output = str(tmp_path / "out.jsonl")

    fake_records_a = [{
        "title": "DS at Amazon", "company": "Amazon", "location": "X",
        "job_url": "https://amazon.jobs/j/1", "description": None,
        "date_posted": "2026-01-01", "job_type": None, "salary": None,
        "source": "amazon_career", "is_remote": None,
        "source_pass": "career_site", "source_company": "Amazon",
    }]
    fake_records_b = [{
        "title": "DS at Apple", "company": "Apple", "location": "Y",
        "job_url": "https://jobs.apple.com/1", "description": None,
        "date_posted": "2026-01-01", "job_type": None, "salary": None,
        "source": "apple_career", "is_remote": None,
        "source_pass": "career_site", "source_company": "Apple",
    }]

    def fake_fetch(self, query, limit=50):
        return fake_records_a if self.name == "Amazon" else fake_records_b

    with patch("career_scraper.SCRAPERS", {"Amazon": AmazonScraperMock, "Apple": AppleScraperMock}):
        with patch.object(AmazonScraperMock, "fetch_jobs", fake_fetch), \
             patch.object(AppleScraperMock, "fetch_jobs", fake_fetch):
            with pytest.raises(SystemExit) as exc:
                cs.main(["--query", "data scientist", "--output", output, "--append"])
    assert exc.value.code == 0

    lines = open(output).readlines()
    assert len(lines) == 2
    records = [json.loads(l) for l in lines]
    by_company = {r["source_company"]: r for r in records}
    assert "Amazon" in by_company
    assert "Apple" in by_company


def test_cli_skips_failing_scraper_and_continues(tmp_path, capsys):
    output = str(tmp_path / "out.jsonl")

    def boom(self, query, limit=50):
        raise RuntimeError("upstream down")

    def ok(self, query, limit=50):
        return [{
            "title": "DS", "company": "Amazon", "location": "X",
            "job_url": "https://amazon.jobs/j/1", "description": None,
            "date_posted": "2026-01-01", "job_type": None, "salary": None,
            "source": "amazon_career", "is_remote": None,
            "source_pass": "career_site", "source_company": "Amazon",
        }]

    with patch("career_scraper.SCRAPERS", {"Amazon": AmazonScraperMock, "Apple": AppleScraperMock}):
        with patch.object(AmazonScraperMock, "fetch_jobs", ok), \
             patch.object(AppleScraperMock, "fetch_jobs", boom):
            with pytest.raises(SystemExit) as exc:
                cs.main(["--query", "data scientist", "--output", output, "--append"])
    assert exc.value.code == 0
    assert "Apple" in capsys.readouterr().out
    lines = open(output).readlines()
    assert len(lines) == 1


def test_cli_exits_1_when_all_scrapers_fail(tmp_path):
    output = str(tmp_path / "out.jsonl")

    def boom(self, query, limit=50):
        raise RuntimeError("upstream down")

    with patch("career_scraper.SCRAPERS", {"Amazon": AmazonScraperMock, "Apple": AppleScraperMock}):
        with patch.object(AmazonScraperMock, "fetch_jobs", boom), \
             patch.object(AppleScraperMock, "fetch_jobs", boom):
            with pytest.raises(SystemExit) as exc:
                cs.main(["--query", "data scientist", "--output", output, "--append"])
    assert exc.value.code == 1


def test_cli_dedupes_across_scrapers(tmp_path):
    output = str(tmp_path / "out.jsonl")

    shared_url = "https://amazon.jobs/j/1"
    rec_a = {"title": "DS", "company": "Amazon", "location": "X", "job_url": shared_url,
             "description": None, "date_posted": "2026-01-01", "job_type": None,
             "salary": None, "source": "amazon_career", "is_remote": None,
             "source_pass": "career_site", "source_company": "Amazon"}
    rec_b = {**rec_a, "source": "linkedin"}  # same job_url

    def fetch_a(self, query, limit=50):
        return [rec_a]
    def fetch_b(self, query, limit=50):
        return [rec_b]

    with patch("career_scraper.SCRAPERS", {"Amazon": AmazonScraperMock, "Apple": AppleScraperMock}):
        with patch.object(AmazonScraperMock, "fetch_jobs", fetch_a), \
             patch.object(AppleScraperMock, "fetch_jobs", fetch_b):
            with pytest.raises(SystemExit):
                cs.main(["--query", "data scientist", "--output", output, "--append"])

    lines = open(output).readlines()
    assert len(lines) == 1


# --- Mock scraper classes used in tests above ---

from career_scrapers.base import BaseCareerScraper

class AmazonScraperMock(BaseCareerScraper):
    name = "Amazon"
    base_url = "https://amazon.jobs"
    def fetch_jobs(self, query, limit=50):
        return []

class AppleScraperMock(BaseCareerScraper):
    name = "Apple"
    base_url = "https://jobs.apple.com"
    def fetch_jobs(self, query, limit=50):
        return []
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `PYTHONPATH=. /home/can/Desktop/job/.venv/bin/pytest tests/test_career_scraper_cli.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'career_scraper'`.

- [ ] **Step 3: Implement `career_scraper.py`**

```python
"""Big Tech career sites scraper CLI.

Loads every registered scraper from career_scrapers.SCRAPERS, invokes each
in isolation (per-scraper failure does not abort), aggregates the results,
dedupes by job_url, and writes to the output file with --append semantics.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from career_scrapers import SCRAPERS, BaseCareerScraper
from scraper import append_jobs_jsonl, deduplicate_jobs, read_existing_jobs


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Big Tech 7 career-site scraper (Apple, Microsoft, Google, Amazon, Meta, Nvidia, Tesla)"
    )
    p.add_argument("--query", required=True, help="Job search query")
    p.add_argument("--limit", "-n", type=int, default=50, help="Max results per scraper")
    p.add_argument("--hours", "-H", type=int, default=0,
                   help="Filter by age (hours), 0=disabled. Currently a no-op for career sites; reserved for future use.")
    p.add_argument("--output", "-o", default="jobs_career.jsonl", help="Output file path")
    p.add_argument("--append", "-a", action="store_true", help="Append to output file (don't overwrite)")
    p.add_argument("--no-proxy", action="store_true", help="Disable proxy rotation")
    p.add_argument("--proxy", help="Use a specific proxy instead of random")
    return p


def _print_per_scraper_summary(results: dict[str, list[dict]], errors: dict[str, str]) -> None:
    print("\nPer-scraper results:")
    for name in SCRAPERS:
        if name in errors:
            print(f"  ❌ {name}: {errors[name]}")
        else:
            count = len(results.get(name, []))
            print(f"  ✅ {name}: {count} job(s)")


def main(argv: list[str] | None = None) -> int:
    args = _build_argparser().parse_args(argv)

    output: str = args.output
    proxy: str | None = None if args.no_proxy else args.proxy

    existing_urls: set[str] = set()
    if args.append and os.path.exists(output):
        existing_urls = read_existing_jobs(output)
        print(f"Loaded {len(existing_urls)} existing job URLs from {output}")

    results: dict[str, list[dict]] = {}
    errors: dict[str, str] = {}

    for name, scraper_cls in SCRAPERS.items():
        try:
            scraper: BaseCareerScraper = scraper_cls(proxy=proxy)
            records = scraper.fetch_jobs(args.query, limit=args.limit)
            results[name] = records
            print(f"  [{name}] fetched {len(records)} record(s)")
        except Exception as e:
            errors[name] = f"{type(e).__name__}: {e}"
            print(f"  [{name}] FAILED: {errors[name]}")

    _print_per_scraper_summary(results, errors)

    all_records: list[dict] = []
    for recs in results.values():
        all_records.extend(recs)
    all_records = deduplicate_jobs(all_records)

    if not all_records:
        if errors and len(errors) == len(SCRAPERS):
            print("\nAll scrapers failed. Exiting 1.")
            return 1
        print("\nNo records to write. Exiting 0.")
        return 0

    new_count = append_jobs_jsonl(all_records, output, existing_urls)
    print(f"\nWrote {new_count} new job(s) to {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `PYTHONPATH=. /home/can/Desktop/job/.venv/bin/pytest tests/test_career_scraper_cli.py -v`
Expected: PASS — 5 tests.

- [ ] **Step 5: Commit**

```bash
git add career_scraper.py tests/test_career_scraper_cli.py
git commit -m "feat(career_scraper): top-level CLI orchestrator"
```

---

## Task 4: Wire `career_scraper.py` into `run_daily.py` (3rd pass) + `telegram_notify.py` (3rd label)

**Files:**
- Modify: `run_daily.py` (extend `run_summary["scrape"]` + add pass 3 invocation + update exit condition)
- Modify: `telegram_notify.py` (add `career_site` label)
- Modify: `tests/test_analyzer.py` (add 3-pass formatter test)

- [ ] **Step 1: Add the failing test for the 3-pass formatter shape**

Append to `tests/test_analyzer.py`:

```python
def test_format_run_summary_renders_three_pass_breakdown():
    """Three-pass summary: render one row per pass (Turkey + Big Tech 7 + Career sites)."""
    from telegram_notify import format_run_summary
    summary = {
        "proxy_validation": {"working": 1, "total": 1, "selected": "127.0.0.1:8080"},
        "scrape": {
            "turkey_local":    {"found": 8, "new": 4, "status": "success"},
            "big_tech_global": {"found": 3, "new": 2, "status": "success"},
            "career_site":     {"found": 5, "new": 1, "status": "success"},
        },
        "analyze": {"status": "success", "processed": 12, "succeeded": 12, "failed": 0, "error_summary": None},
        "errors": [],
    }
    msg = format_run_summary(summary)
    assert "🇹🇷 Turkey local" in msg
    assert "🌍 Big Tech 7" in msg
    assert "🏢 Career sites" in msg
    assert "Found: 5" in msg
    assert "✅ *SUCCESS*" in msg


def test_format_run_summary_career_site_failure_does_not_kill_run():
    from telegram_notify import format_run_summary
    summary = {
        "proxy_validation": {"working": 1, "total": 1, "selected": "127.0.0.1:8080"},
        "scrape": {
            "turkey_local":    {"found": 8, "new": 4, "status": "success"},
            "big_tech_global": {"found": 3, "new": 2, "status": "success"},
            "career_site":     {"found": 0, "new": 0, "status": "failed"},
        },
        "analyze": {"status": "success", "processed": 6, "succeeded": 6, "failed": 0, "error_summary": None},
        "errors": [],
    }
    msg = format_run_summary(summary)
    assert "❌ 🏢 Career sites" in msg
    # Turkey + Big Tech still pass, so overall is success.
    assert "✅ *SUCCESS*" in msg
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `PYTHONPATH=. /home/can/Desktop/job/.venv/bin/pytest tests/test_analyzer.py::test_format_run_summary_renders_three_pass_breakdown tests/test_analyzer.py::test_format_run_summary_career_site_failure_does_not_kill_run -v`
Expected: FAIL — the 3rd pass key isn't rendered yet.

- [ ] **Step 3: Update `telegram_notify.py` `pass_labels`**

Find the `pass_labels` dict in `telegram_notify.py:131-135`. Replace:

```python
    pass_labels = {
        "turkey_local":    "🇹🇷 Turkey local",
        "big_tech_global": "🌍 Big Tech 7",
    }
```

With:

```python
    pass_labels = {
        "turkey_local":    "🇹🇷 Turkey local",
        "big_tech_global": "🌍 Big Tech 7",
        "career_site":     "🏢 Career sites",
    }
```

- [ ] **Step 4: Re-run formatter tests, verify pass**

Run: `PYTHONPATH=. /home/can/Desktop/job/.venv/bin/pytest tests/test_analyzer.py -k "three_pass or career_site" -v`
Expected: PASS.

- [ ] **Step 5: Update `run_daily.py` — add `career_site` bucket and 3rd pass**

In `run_daily.py`, find the `run_summary` initialization (around line 32). Replace:

```python
    "scrape": {
        "turkey_local":    {"found": 0, "new": 0, "status": "not_run"},
        "big_tech_global": {"found": 0, "new": 0, "status": "not_run"},
    },
```

With:

```python
    "scrape": {
        "turkey_local":    {"found": 0, "new": 0, "status": "not_run"},
        "big_tech_global": {"found": 0, "new": 0, "status": "not_run"},
        "career_site":     {"found": 0, "new": 0, "status": "not_run"},
    },
```

Find the Big Tech 7 pass invocation (around line 269) and the failure-exit. Replace:

```python
    print("  -> Pass 2: Big Tech 7 (global, company-filtered)")
    scrape_ok_b = run_command([
        PYTHON, "scraper.py",
        "--query", "data scientist",
        "--country", "worldwide",
        "--big-tech",
        "--hours", "1",
        "--output", "jobs_linkedin.jsonl",
        "--proxy", proxy,
        "--append",
    ], "Scraping Big Tech 7 jobs")
    _update_pass_summary("big_tech_global", scrape_ok_b)

    if not (scrape_ok_a or scrape_ok_b):
        run_summary["analyze"]["status"] = "skipped"
        print_summary()
        sys.exit(1)
```

With:

```python
    print("  -> Pass 2: Big Tech 7 (global, company-filtered)")
    scrape_ok_b = run_command([
        PYTHON, "scraper.py",
        "--query", "data scientist",
        "--country", "worldwide",
        "--big-tech",
        "--hours", "1",
        "--output", "jobs_linkedin.jsonl",
        "--proxy", proxy,
        "--append",
    ], "Scraping Big Tech 7 jobs")
    _update_pass_summary("big_tech_global", scrape_ok_b)

    print("  -> Pass 3: Big Tech career sites (direct, all 7)")
    scrape_ok_c = run_command([
        PYTHON, "career_scraper.py",
        "--query", "data scientist",
        "--hours", "168",                # 7 days — career sites update less often
        "--output", "jobs_linkedin.jsonl",
        "--proxy", proxy,
        "--append",
    ], "Scraping Big Tech career sites")
    _update_pass_summary("career_site", scrape_ok_c)

    if not (scrape_ok_a or scrape_ok_b or scrape_ok_c):
        run_summary["analyze"]["status"] = "skipped"
        print_summary()
        sys.exit(1)
```

- [ ] **Step 6: Run full test suite, verify all green**

Run: `PYTHONPATH=. /home/can/Desktop/job/.venv/bin/pytest tests/ -q`
Expected: PASS — 64 tests (61 prior + 3 new).

- [ ] **Step 7: Commit**

```bash
git add run_daily.py telegram_notify.py tests/test_analyzer.py
git commit -m "feat: wire career_scraper.py into run_daily as 3rd pass + Telegram summary row"
```

---

## Task 5: Add 6 more company scrapers (one per file)

This task is structured as 6 sub-steps, one per company. Each is independent and the engineer can do them in any order. Per the recon, expect:
- **Tier 2 (Google, Meta, Microsoft)**: API may need research (browser dev tools) and a few extra headers. If the endpoint is unknown, save a 200-line stub that returns `[]` and log a TODO.
- **Tier 3 (Apple, Nvidia, Tesla)**: Likely stubs that return `[]` — the cron logs will show "0 jobs" for these and we can revisit later.

The contract for every scraper is the same: `name`, `base_url`, `fetch_jobs(query, limit) -> list[dict]`. Use `self._get(url, headers=...)` for HTTP and `self._make_record(...)` for output.

**For each sub-step below:** create the file, write the implementation (real or stub), add a happy-path test, commit.

### Step 5.1: GoogleScraper (tier-2)

- [ ] **Create `career_scrapers/google.py`**

```python
"""Google careers scraper.

NOTE: Endpoint discovery required. careers.google.com/api/v3/search/ returned
404 in plan-time recon. Subclass overrides fetch_jobs to use the discovered
endpoint, or returns [] until research is done.
"""

from career_scrapers.base import BaseCareerScraper


class GoogleScraper(BaseCareerScraper):
    name = "Google"
    base_url = "https://careers.google.com"
    rate_limit_seconds = 1.5   # Google is more strict; back off a bit

    def fetch_jobs(self, query: str, limit: int = 50) -> list[dict]:
        # TODO: discover the correct search endpoint via browser dev tools,
        # then replace this stub with the real implementation.
        # The public search page is https://careers.google.com/jobs/results/
        # which is a SPA — likely needs a POST to an internal API.
        return []
```

- [ ] **Add test** (append to `tests/test_career_scrapers.py`):

```python
def test_google_scraper_returns_empty_until_endpoint_discovered():
    from career_scrapers.google import GoogleScraper
    s = GoogleScraper()
    # Google is a stub until the endpoint is discovered — must not raise.
    assert s.fetch_jobs("data scientist") == []
```

- [ ] **Commit**: `git commit -am "feat(career_scrapers): add GoogleScraper stub (tier-2)"`

### Step 5.2: MetaScraper (tier-2)

- [ ] **Create `career_scrapers/meta.py`**

```python
"""Meta careers scraper.

NOTE: metacareers.com/graphql returned 200 with HTML error in plan-time
recon. Likely a GraphQL endpoint that needs CSRF token + proper headers.
Stub for now; revisit when the endpoint is documented.
"""

from career_scrapers.base import BaseCareerScraper


class MetaScraper(BaseCareerScraper):
    name = "Meta"
    base_url = "https://www.metacareers.com"
    rate_limit_seconds = 1.5

    def fetch_jobs(self, query: str, limit: int = 50) -> list[dict]:
        # TODO: replace with GraphQL POST after endpoint/CSRF research.
        return []
```

- [ ] **Add test** (append to `tests/test_career_scrapers.py`):

```python
def test_meta_scraper_returns_empty_until_endpoint_discovered():
    from career_scrapers.meta import MetaScraper
    s = MetaScraper()
    assert s.fetch_jobs("data scientist") == []
```

- [ ] **Commit**: `git commit -am "feat(career_scrapers): add MetaScraper stub (tier-2)"`

### Step 5.3: MicrosoftScraper (tier-2)

- [ ] **Create `career_scrapers/microsoft.py`**

```python
"""Microsoft careers scraper.

NOTE: careers.microsoft.com/api/v1/roles returned an HTML page in
plan-time recon. Their careers site is a SPA; the JSON API is
discoverable via browser dev tools. Stub for now.
"""

from career_scrapers.base import BaseCareerScraper


class MicrosoftScraper(BaseCareerScraper):
    name = "Microsoft"
    base_url = "https://careers.microsoft.com"
    rate_limit_seconds = 1.5

    def fetch_jobs(self, query: str, limit: int = 50) -> list[dict]:
        # TODO: discover the JSON endpoint via the SPA's network calls.
        return []
```

- [ ] **Add test** (append to `tests/test_career_scrapers.py`):

```python
def test_microsoft_scraper_returns_empty_until_endpoint_discovered():
    from career_scrapers.microsoft import MicrosoftScraper
    s = MicrosoftScraper()
    assert s.fetch_jobs("data scientist") == []
```

- [ ] **Commit**: `git commit -am "feat(career_scrapers): add MicrosoftScraper stub (tier-2)"`

### Step 5.4: AppleScraper (tier-3)

- [ ] **Create `career_scrapers/apple.py`**

```python
"""Apple careers scraper.

NOTE: jobs.apple.com/api/v1/jobListings returned 401 in plan-time recon.
No public API; search results are server-rendered HTML at
https://jobs.apple.com/en-us/search. Full implementation likely needs
HTML scraping. Stub for now.
"""

from career_scrapers.base import BaseCareerScraper


class AppleScraper(BaseCareerScraper):
    name = "Apple"
    base_url = "https://jobs.apple.com"
    rate_limit_seconds = 2.0

    def fetch_jobs(self, query: str, limit: int = 50) -> list[dict]:
        # TODO: HTML-scrape https://jobs.apple.com/en-us/search?search={query}
        # when Playwright/headless browser is added (out of scope for this plan).
        return []
```

- [ ] **Add test** (append to `tests/test_career_scrapers.py`):

```python
def test_apple_scraper_returns_empty_html_only():
    from career_scrapers.apple import AppleScraper
    s = AppleScraper()
    assert s.fetch_jobs("data scientist") == []
```

- [ ] **Commit**: `git commit -am "feat(career_scrapers): add AppleScraper stub (tier-3)"`

### Step 5.5: NvidiaScraper (tier-3, Workday)

- [ ] **Create `career_scrapers/nvidia.py`**

```python
"""Nvidia careers scraper.

Uses Workday (nvidia.wd5.myworkdayjobs.com). Workday is a known difficult
target: it requires a session-establishment POST (the "apply" redirect
seen in plan-time recon) to obtain a CSRF token, then subsequent API
calls. Stub for now; revisit in a follow-up plan if real Workday
integration is needed.
"""

from career_scrapers.base import BaseCareerScraper


class NvidiaScraper(BaseCareerScraper):
    name = "Nvidia"
    base_url = "https://nvidia.wd5.myworkdayjobs.com"
    rate_limit_seconds = 2.0

    def fetch_jobs(self, query: str, limit: int = 50) -> list[dict]:
        # TODO: Workday session-establishment flow + job-search API.
        return []
```

- [ ] **Add test** (append to `tests/test_career_scrapers.py`):

```python
def test_nvidia_scraper_returns_empty_workday():
    from career_scrapers.nvidia import NvidiaScraper
    s = NvidiaScraper()
    assert s.fetch_jobs("data scientist") == []
```

- [ ] **Commit**: `git commit -am "feat(career_scrapers): add NvidiaScraper stub (tier-3, Workday)"`

### Step 5.6: TeslaScraper (tier-3)

- [ ] **Create `career_scrapers/tesla.py`**

```python
"""Tesla careers scraper.

NOTE: tesla.com/careers/api/jobs returned 403 in plan-time recon. Tesla's
careers page is server-rendered; may need HTML scraping or authenticated
access. Stub for now.
"""

from career_scrapers.base import BaseCareerScraper


class TeslaScraper(BaseCareerScraper):
    name = "Tesla"
    base_url = "https://www.tesla.com"
    rate_limit_seconds = 2.0

    def fetch_jobs(self, query: str, limit: int = 50) -> list[dict]:
        # TODO: HTML scrape https://www.tesla.com/careers/search when
        # Playwright/headless browser is added (out of scope for this plan).
        return []
```

- [ ] **Add test** (append to `tests/test_career_scrapers.py`):

```python
def test_tesla_scraper_returns_empty_blocked():
    from career_scrapers.tesla import TeslaScraper
    s = TeslaScraper()
    assert s.fetch_jobs("data scientist") == []
```

- [ ] **Commit**: `git commit -am "feat(career_scrapers): add TeslaScraper stub (tier-3)"`

### Step 5.7: Register all 6 new scrapers in `career_scrapers/__init__.py`

- [ ] **Update `career_scrapers/__init__.py`** to import the new modules and add them to the registry:

```python
"""Big Tech 7 career-site scrapers.

Each module registers a concrete scraper class by importing it in
`__all__` below; the SCRAPERS dict is auto-populated.
"""
from career_scrapers.base import BaseCareerScraper

from career_scrapers.amazon import AmazonScraper
from career_scrapers.google import GoogleScraper
from career_scrapers.meta import MetaScraper
from career_scrapers.microsoft import MicrosoftScraper
from career_scrapers.apple import AppleScraper
from career_scrapers.nvidia import NvidiaScraper
from career_scrapers.tesla import TeslaScraper

SCRAPERS: dict[str, type[BaseCareerScraper]] = {
    cls.name: cls
    for cls in [
        AmazonScraper,
        GoogleScraper,
        MetaScraper,
        MicrosoftScraper,
        AppleScraper,
        NvidiaScraper,
        TeslaScraper,
    ]
}

__all__ = ["BaseCareerScraper", "SCRAPERS"]
```

- [ ] **Add a registry-completeness test** (append to `tests/test_career_scrapers.py`):

```python
def test_registry_contains_all_seven_big_tech():
    expected = {"Apple", "Microsoft", "Google", "Amazon", "Meta", "Nvidia", "Tesla"}
    assert set(SCRAPERS.keys()) == expected
```

- [ ] **Run full suite, verify all green**

Run: `PYTHONPATH=. /home/can/Desktop/job/.venv/bin/pytest tests/ -q`
Expected: PASS — 71 tests (64 prior + 1 registry test + 6 stub tests).

- [ ] **Commit**:

```bash
git add career_scrapers/__init__.py tests/test_career_scrapers.py
git commit -m "feat(career_scrapers): register all 7 Big Tech scrapers"
```

---

## Task 6: Live smoke test (manual, no commit)

- [ ] **Step 1: Run `career_scraper.py` standalone against Amazon only**

This validates the orchestrator end-to-end without involving all 6 stubs:

```bash
PYTHONPATH=. .venv/bin/python -c "
from career_scrapers import SCRAPERS
# Temporarily narrow to Amazon for a clean test
import career_scrapers
career_scrapers.SCRAPERS = {'Amazon': career_scrapers.SCRAPERS['Amazon']}
from career_scraper import main
import sys
sys.exit(main(['--query', 'data scientist', '--limit', '5', '--no-proxy', '--output', '/tmp/test_career.jsonl', '--append']))
"
```

Expected: prints `✅ Amazon: N job(s)` (N > 0 if Amazon's API returned results; may be 0 if it rate-limited). Exit 0.

- [ ] **Step 2: Run with all 7 scrapers**

```bash
PYTHONPATH=. .venv/bin/python career_scraper.py --query "data scientist" --limit 5 --no-proxy \
    --output /tmp/test_career_all.jsonl --append
```

Expected output (approximate):
```
  [Amazon] fetched N job(s)
  [Google] FAILED: ...
  [Meta] FAILED: ...
  [Microsoft] FAILED: ...
  [Apple] FAILED: ...
  [Nvidia] FAILED: ...
  [Tesla] FAILED: ...

Per-scraper results:
  ✅ Amazon: N job(s)
  ❌ Google: ...
  ❌ Meta: ...
  ...
```

Exit code 0 (because Amazon contributed >0 jobs; if all failed, exit 1).

- [ ] **Step 3: Verify the JSONL has the expected `source_pass` tag**

```bash
jq -c 'select(.source_pass=="career_site")' /tmp/test_career_all.jsonl | head -3
jq -c 'select(.source_pass=="career_site")' /tmp/test_career_all.jsonl | jq -r '.source_company' | sort | uniq -c
```

Expected: at least 1 record with `source_pass="career_site"`. The per-company tally shows Amazon count >= 1, others = 0 (since they're stubs).

- [ ] **Step 4: Run a full `run_daily.py` cycle (optional, takes longer)**

```bash
PYTHONPATH=. .venv/bin/python run_daily.py >> cron.log 2>&1
tail -50 cron.log
```

Expected: cron.log shows all three passes (Turkey, Big Tech 7, Career sites) with the new `🏢 Career sites` row.

---

## Self-Review

**1. Spec coverage:**

| Spec section                                      | Task(s)        |
|---------------------------------------------------|----------------|
| `career_scrapers/` package                        | Task 1         |
| `BaseCareerScraper` abstract class                | Task 1         |
| `AmazonScraper` (tier-1)                          | Task 2         |
| `GoogleScraper` (tier-2)                          | Task 5.1       |
| `MetaScraper` (tier-2)                            | Task 5.2       |
| `MicrosoftScraper` (tier-2)                       | Task 5.3       |
| `AppleScraper` (tier-3)                           | Task 5.4       |
| `NvidiaScraper` (tier-3, Workday)                 | Task 5.5       |
| `TeslaScraper` (tier-3)                           | Task 5.6       |
| `career_scraper.py` CLI                           | Task 3         |
| Registry in `__init__.py`                         | Tasks 1, 5.7   |
| Record schema (`source_pass`, `source_company`)   | Task 1 (`_make_record`) |
| Per-scraper failure isolation                     | Task 3 (CLI `try/except`) |
| Exit codes (0 if any scraper contributed; 1 if all failed) | Task 3 |
| Dedup by `job_url`                                | Task 3 (calls `scraper.deduplicate_jobs`) |
| `run_daily.py` 3rd pass + `career_site` bucket    | Task 4         |
| `telegram_notify.py` 3rd label                    | Task 4         |
| Per-pass formatter test                           | Task 4         |
| Unit tests for base + per-company                 | Tasks 1, 2, 5.x |
| CLI tests (registry, dedup, failure isolation)    | Task 3         |
| Live smoke test                                   | Task 6         |
| `tests/fixtures/career_sites/amazon.json`         | Task 2         |

**2. Placeholder scan:** No "TBD", "TODO" in the *plan steps themselves* (the TODO comments inside scraper source files are documented limitations, not plan failures — they tell the engineer that the endpoint is not yet discovered and the stub is intentional). No "similar to Task N" — each company step has its own complete code block. No vague "implement error handling" — all retry logic is concrete in Task 1.

**3. Type consistency:**
- `BaseCareerScraper.name: ClassVar[str]`, `base_url: ClassVar[str]` → used identically in every concrete scraper.
- `BaseCareerScraper.fetch_jobs(self, query: str, limit: int = 50) -> list[dict]` → every concrete scraper matches this signature.
- `BaseCareerScraper._make_record(...) -> dict` → used identically; returns the exact record shape.
- `SCRAPERS: dict[str, type[BaseCareerScraper]]` → Task 5.7 populates it with all 7 classes.
- `career_scraper.SCRAPERS` import in test (line 29 of test_career_scraper_cli.py) matches the same name in `career_scrapers/__init__.py`.

No inconsistencies found.

**4. One potential improvement to flag for the engineer:** Task 5's per-company steps (5.1–5.6) include per-step commits. If the engineer prefers fewer commits, they can amend them into a single commit at the end. The plan structure is designed for incremental review; collapsing is fine.
