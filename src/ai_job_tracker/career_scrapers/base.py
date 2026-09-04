"""Abstract base for Big Tech career-site scrapers."""

from __future__ import annotations

import time
import urllib.error
import urllib.request
from typing import Any, ClassVar


class BaseCareerScraper:
    """Abstract base for one company's career-site scraper.

    Subclasses must set `name` and `base_url` as class vars, and override
    `fetch_jobs(query, limit) -> list[dict]`. A source opts into execution only
    after setting `operational = True`. The framework provides throttling,
    retry, and a record-builder helper that fills `source_pass` and
    `source_company` automatically.
    """

    name: ClassVar[str] = ""
    base_url: ClassVar[str] = ""
    operational: ClassVar[bool] = False
    rate_limit_seconds: ClassVar[float] = 1.0
    # Max total attempts (first try + retries). 3 means: try once, retry up to 2 times.
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
        if self.proxy:
            # Proxy path uses a dedicated opener; not interchangeable with the
            # plain `urlopen` call below (and therefore not currently covered
            # by the urlopen-patch-based retry tests).
            proxy_handler = urllib.request.ProxyHandler({
                "http": self.proxy,
                "https": self.proxy,
            })
            opener = urllib.request.build_opener(proxy_handler)
        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                if self.proxy:
                    with opener.open(req, timeout=30) as r:
                        return r.read()
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
        """Build a record matching the common record schema.

        Required kwargs: title, company, location, job_url.
        Optional kwargs: description, date_posted, source, is_remote, salary.

        Fields filled with defaults:
          - description: passed through (None if omitted)
          - date_posted: "unknown" if omitted/empty
          - job_type: None
          - salary: passed through (None if omitted)
          - source: f"{self.name.lower()}_career" if omitted
          - is_remote: passed through (None if omitted)
          - source_pass: "career_site"
          - source_company: self.name
        """
        return {
            "title": title,
            "company": company,
            "location": location,
            "job_url": job_url,
            "description": description,
            "date_posted": date_posted or "unknown",
            "job_type": None,
            "salary": salary,
            "source": source or f"{self.name.lower()}_career",
            "is_remote": is_remote,
            "source_pass": "career_site",
            "source_company": self.name,
        }
