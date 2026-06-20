"""Amazon careers scraper.

Uses the public JSON API at https://amazon.jobs/en/search.json.
No auth required; throttled to 1.0s between requests.

Implements :meth:`BaseCareerScraper.fetch_jobs`, returning records shaped
to the common record schema (see ``base._make_record``).
"""

import json

from career_scrapers.base import BaseCareerScraper


class AmazonScraper(BaseCareerScraper):
    """Scrape Amazon's public jobs search JSON endpoint.

    Class vars:
      - name: "Amazon" (canonical company name used in records)
      - base_url: "https://amazon.jobs" (used to resolve relative job_paths)
      - rate_limit_seconds: 1.0 (gentle throttle for the unauthenticated API)
      - SEARCH_URL: full JSON endpoint URL

    Records returned by :meth:`fetch_jobs` always carry:
      - title from API ``job.title``
      - company = self.name ("Amazon") — NOT whatever ``company_name`` the
        API returns (which can be "Amazon.com Services LLC" and varies).
      - location from API ``job.location`` (e.g. "US, TX, Austin")
      - job_url = f"https://amazon.jobs{job['job_path']}" (resolved relative path)
      - description from API ``job.description``
      - date_posted from API ``job.posted_date`` (e.g. "May  7, 2026")
      - source_pass / source_company / source filled by ``_make_record``
    """

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
            job_path = job.get("job_path", "")
            records.append(self._make_record(
                title=job.get("title", ""),
                company=self.name,
                location=job.get("location", ""),
                job_url=f"{self.base_url}{job_path}",
                description=job.get("description"),
                date_posted=job.get("posted_date"),
            ))
        return records
