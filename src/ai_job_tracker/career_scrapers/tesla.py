"""Tesla careers scraper (tier-3: stub — endpoint blocked).

tesla.com/careers/api/jobs returned 403 in plan-time recon. Tesla's
careers page is server-rendered; HTML scraping would need a headless
browser (Playwright), out of scope for this plan.
"""

from ai_job_tracker.career_scrapers.base import BaseCareerScraper


class TeslaScraper(BaseCareerScraper):
    name = "Tesla"
    base_url = "https://www.tesla.com"
    rate_limit_seconds = 2.0

    def fetch_jobs(self, query: str, limit: int = 50) -> list[dict]:
        return []