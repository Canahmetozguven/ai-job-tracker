"""Meta careers scraper (tier-2: stub — endpoint exists but returns HTML error).

metacareers.com/graphql returned 200 with an HTML body in plan-time recon,
indicating the endpoint exists but requires CSRF/cookies + a proper
GraphQL POST. The query language and authentication mechanism need
further research.
"""

from career_scrapers.base import BaseCareerScraper


class MetaScraper(BaseCareerScraper):
    name = "Meta"
    base_url = "https://www.metacareers.com"
    rate_limit_seconds = 1.5

    def fetch_jobs(self, query: str, limit: int = 50) -> list[dict]:
        return []