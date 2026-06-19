"""Big Tech 7 career-site scrapers.

Each module that defines a concrete scraper is imported here and added to
the SCRAPERS registry below.
"""
from career_scrapers.base import BaseCareerScraper

# Concrete scrapers (added in later tasks)
from career_scrapers.amazon import AmazonScraper

SCRAPERS: dict[str, type[BaseCareerScraper]] = {
    cls.name: cls
    for cls in [AmazonScraper]
}

__all__ = ["BaseCareerScraper", "SCRAPERS"]
