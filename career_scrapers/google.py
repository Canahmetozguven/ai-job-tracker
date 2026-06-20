"""Google careers scraper (tier-2: stub — endpoint not yet discovered).

careers.google.com/api/v3/search/ returned 404 in plan-time recon.
Google's careers search is a SPA at https://careers.google.com/jobs/results/;
the JSON API is undocumented and likely needs browser dev-tools research
to find the correct POST endpoint + parameters.
"""

from career_scrapers.base import BaseCareerScraper


class GoogleScraper(BaseCareerScraper):
    name = "Google"
    base_url = "https://careers.google.com"
    rate_limit_seconds = 1.5

    def fetch_jobs(self, query: str, limit: int = 50) -> list[dict]:
        return []