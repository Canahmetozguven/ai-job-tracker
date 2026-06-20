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

import json
from urllib.parse import urlencode

from career_scrapers.base import BaseCareerScraper


class AmazonScraper(BaseCareerScraper):
    name = "Amazon"
    base_url = "https://amazon.jobs"
    rate_limit_seconds = 1.0

    SEARCH_URL = "https://amazon.jobs/en/search.json"

    def fetch_jobs(self, query: str, limit: int = 50) -> list[dict]:
        # Amazon's search is driven by `base_query` (not `keywords`). Use
        # urlencode so spaces/special chars in `query` are properly escaped.
        params = urlencode({"base_query": query, "loc_query": "", "result_limit": limit})
        url = f"{self.SEARCH_URL}?{params}"
        body = self._get(url)
        data = json.loads(body)
        records = []
        for job in data.get("jobs", []):
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
