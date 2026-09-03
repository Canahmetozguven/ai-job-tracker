"""Microsoft careers scraper (tier-2: stub — JSON endpoint not yet found).

careers.microsoft.com/api/v1/roles returned an HTML page in plan-time recon.
Their careers site is a SPA; the JSON API powering it is discoverable via
browser dev-tools network inspection.
"""

from ai_job_tracker.career_scrapers.base import BaseCareerScraper


class MicrosoftScraper(BaseCareerScraper):
    name = "Microsoft"
    base_url = "https://careers.microsoft.com"
    rate_limit_seconds = 1.5

    def fetch_jobs(self, query: str, limit: int = 50) -> list[dict]:
        return []