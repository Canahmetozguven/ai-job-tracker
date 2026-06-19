"""Big Tech 7 career-site scrapers.

Each module registers a concrete scraper class by importing it in
`__all__` below; the SCRAPERS dict is auto-populated.
"""
from career_scrapers.base import BaseCareerScraper

# Concrete scrapers (added in later tasks)
from career_scrapers.amazon import AmazonScraper

SCRAPERS: dict[str, type[BaseCareerScraper]] = {
    cls.name: cls
    for cls in [AmazonScraper]
}

__all__ = ["BaseCareerScraper", "SCRAPERS"]
