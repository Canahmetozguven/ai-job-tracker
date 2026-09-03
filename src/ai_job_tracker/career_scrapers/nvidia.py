"""Nvidia careers scraper (tier-3: stub — Workday session flow needed).

nvidia.wd5.myworkdayjobs.com is a Workday tenant. Workday requires a
session-establishment POST (the "apply" redirect seen in plan-time recon)
to obtain a CSRF token, then subsequent API calls. The session flow +
API surface need separate research and a custom client.
"""

from ai_job_tracker.career_scrapers.base import BaseCareerScraper


class NvidiaScraper(BaseCareerScraper):
    name = "Nvidia"
    base_url = "https://nvidia.wd5.myworkdayjobs.com"
    rate_limit_seconds = 2.0

    def fetch_jobs(self, query: str, limit: int = 50) -> list[dict]:
        return []