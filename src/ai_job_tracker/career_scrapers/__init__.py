"""Big Tech 7 career-site scrapers.

Scrapers are registered by importing each concrete class at the top and
adding it to the SCRAPERS dict comprehension below. Tier-1 (Amazon) is a
working implementation; tier-2/3 scrapers are stubs returning [] that
log their failure via the CLI and can be filled in later.
"""
from ai_job_tracker.career_scrapers.base import BaseCareerScraper

from ai_job_tracker.career_scrapers.amazon import AmazonScraper
from ai_job_tracker.career_scrapers.google import GoogleScraper
from ai_job_tracker.career_scrapers.meta import MetaScraper
from ai_job_tracker.career_scrapers.microsoft import MicrosoftScraper
from ai_job_tracker.career_scrapers.apple import AppleScraper
from ai_job_tracker.career_scrapers.nvidia import NvidiaScraper
from ai_job_tracker.career_scrapers.tesla import TeslaScraper

SCRAPERS: dict[str, type[BaseCareerScraper]] = {
    cls.name: cls
    for cls in [
        AmazonScraper,
        GoogleScraper,
        MetaScraper,
        MicrosoftScraper,
        AppleScraper,
        NvidiaScraper,
        TeslaScraper,
    ]
}

__all__ = ["BaseCareerScraper", "SCRAPERS"]
