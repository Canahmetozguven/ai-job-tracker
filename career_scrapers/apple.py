"""Apple careers scraper (tier-3: stub — public API requires auth).

jobs.apple.com/api/v1/jobListings returned 401 in plan-time recon, indicating
the endpoint exists but requires authentication. The public search results
at https://jobs.apple.com/en-us/search are server-rendered HTML, which
would need HTML scraping to extract jobs — out of scope for this plan
(needs Playwright/headless browser).
"""

from career_scrapers.base import BaseCareerScraper


class AppleScraper(BaseCareerScraper):
    name = "Apple"
    base_url = "https://jobs.apple.com"
    rate_limit_seconds = 2.0

    def fetch_jobs(self, query: str, limit: int = 50) -> list[dict]:
        return []