"""Amazon careers scraper.

Uses the public JSON API at https://amazon.jobs/en/search.json.
No auth required; throttled to 1.0s between requests.

Field mapping from API response -> record:
  title       <- jobs[].title
  company     -> self.name ("Amazon")  [canonical, NOT API's "Amazon.com Services LLC"]
  location    <- jobs[].location
  job_url     -> self.base_url + jobs[].job_path   [API returns a relative path]
  description <- jobs[].description
  date_posted <- jobs[].posted_date

Records with missing title or job_path are skipped — they cannot produce
a usable record and would otherwise pollute the JSONL with homepage URLs.
"""

import datetime
import json
from urllib.parse import urlencode

from ai_job_tracker.career_freshness import filter_recent_jobs
from ai_job_tracker.career_scrapers.base import BaseCareerScraper


class AmazonScraper(BaseCareerScraper):
    name = "Amazon"
    base_url = "https://amazon.jobs"
    rate_limit_seconds = 1.0

    SEARCH_URL = "https://amazon.jobs/en/search.json"
    PAGE_SIZE = 50

    def _fetch_page(self, query: str, limit: int, offset: int) -> dict:
        # Amazon's search is driven by `base_query` (not `keywords`). Use
        # urlencode so spaces/special chars in `query` are properly escaped.
        params = urlencode({
            "base_query": query,
            "loc_query": "",
            "result_limit": limit,
            "offset": offset,
        })
        url = f"{self.SEARCH_URL}?{params}"
        body = self._get(url)
        return json.loads(body)

    def _parse_jobs(self, jobs: list[dict]) -> list[dict]:
        records = []
        for job in jobs:
            title = job.get("title", "")
            job_path = job.get("job_path", "")
            if not title or not job_path:
                # Skip records that would produce a homepage URL or no title.
                continue
            records.append(self._make_record(
                title=title,
                company=self.name,                                # canonical
                location=job.get("location", ""),
                job_url=f"{self.base_url}{job_path}",
                description=job.get("description"),
                date_posted=job.get("posted_date"),
            ))
        return records

    def fetch_jobs(self, query: str, limit: int = 50) -> list[dict]:
        if limit <= 0:
            return []
        page = self._fetch_page(query, limit, offset=0)
        return self._parse_jobs(page.get("jobs", []))

    def fetch_recent_jobs(
        self,
        query: str,
        limit: int = 50,
        hours: int = 0,
        *,
        current_time: datetime.datetime | None = None,
    ) -> list[dict]:
        """Page through score-sorted results until enough recent jobs are found."""
        if hours <= 0:
            return self.fetch_jobs(query, limit=limit)
        if limit <= 0:
            return []

        reference_time = current_time or datetime.datetime.now(datetime.UTC)
        recent_records = []
        offset = 0
        page_size = self.PAGE_SIZE

        while len(recent_records) < limit:
            page = self._fetch_page(query, page_size, offset)
            jobs = page.get("jobs", [])
            recent_records.extend(
                filter_recent_jobs(self._parse_jobs(jobs), hours, current_time=reference_time)
            )
            offset += len(jobs)

            total_hits = page.get("hits")
            source_exhausted = not jobs or (
                isinstance(total_hits, int) and offset >= total_hits
            )
            if source_exhausted or (not isinstance(total_hits, int) and len(jobs) < page_size):
                break

        return recent_records[:limit]
