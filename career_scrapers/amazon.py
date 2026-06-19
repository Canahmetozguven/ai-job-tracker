"""Amazon careers scraper (placeholder — implemented in Task 2)."""

from career_scrapers.base import BaseCareerScraper


class AmazonScraper(BaseCareerScraper):
    name = "Amazon"
    base_url = "https://amazon.jobs"

    def fetch_jobs(self, query: str, limit: int = 50) -> list[dict]:
        return []
