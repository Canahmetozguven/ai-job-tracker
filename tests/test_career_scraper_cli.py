"""Tests for career_scraper.py CLI (orchestrator)."""

import json
import sys
from unittest.mock import patch, MagicMock

import pytest

import career_scraper as cs
from career_scrapers.base import BaseCareerScraper


class AmazonScraperMock(BaseCareerScraper):
    name = "Amazon"
    base_url = "https://amazon.jobs"

    def fetch_jobs(self, query, limit=50):
        return []


class AppleScraperMock(BaseCareerScraper):
    name = "Apple"
    base_url = "https://jobs.apple.com"

    def fetch_jobs(self, query, limit=50):
        return []


def test_cli_help_shows_expected_flags(capsys):
    with pytest.raises(SystemExit) as exc:
        cs.main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    for flag in ["--query", "--limit", "--proxy", "--output", "--append"]:
        assert flag in out


def test_cli_invokes_each_registered_scraper(tmp_path):
    output = str(tmp_path / "out.jsonl")

    fake_records_a = [{
        "title": "DS at Amazon", "company": "Amazon", "location": "X",
        "job_url": "https://amazon.jobs/j/1", "description": None,
        "date_posted": "2026-01-01", "job_type": None, "salary": None,
        "source": "amazon_career", "is_remote": None,
        "source_pass": "career_site", "source_company": "Amazon",
    }]
    fake_records_b = [{
        "title": "DS at Apple", "company": "Apple", "location": "Y",
        "job_url": "https://jobs.apple.com/1", "description": None,
        "date_posted": "2026-01-01", "job_type": None, "salary": None,
        "source": "apple_career", "is_remote": None,
        "source_pass": "career_site", "source_company": "Apple",
    }]

    def fake_fetch(self, query, limit=50):
        return fake_records_a if self.name == "Amazon" else fake_records_b

    with patch.dict(cs.SCRAPERS, {"Amazon": AmazonScraperMock, "Apple": AppleScraperMock}):
        with patch.object(AmazonScraperMock, "fetch_jobs", fake_fetch), \
             patch.object(AppleScraperMock, "fetch_jobs", fake_fetch):
            with pytest.raises(SystemExit) as exc:
                cs.main(["--query", "data scientist", "--output", output, "--append"])
    assert exc.value.code == 0

    lines = open(output).readlines()
    assert len(lines) == 2
    records = [json.loads(l) for l in lines]
    by_company = {r["source_company"]: r for r in records}
    assert "Amazon" in by_company
    assert "Apple" in by_company


def test_cli_skips_failing_scraper_and_continues(tmp_path, capsys):
    output = str(tmp_path / "out.jsonl")

    def boom(self, query, limit=50):
        raise RuntimeError("upstream down")

    def ok(self, query, limit=50):
        return [{
            "title": "DS", "company": "Amazon", "location": "X",
            "job_url": "https://amazon.jobs/j/1", "description": None,
            "date_posted": "2026-01-01", "job_type": None, "salary": None,
            "source": "amazon_career", "is_remote": None,
            "source_pass": "career_site", "source_company": "Amazon",
        }]

    with patch.dict(cs.SCRAPERS, {"Amazon": AmazonScraperMock, "Apple": AppleScraperMock}):
        with patch.object(AmazonScraperMock, "fetch_jobs", ok), \
             patch.object(AppleScraperMock, "fetch_jobs", boom):
            with pytest.raises(SystemExit) as exc:
                cs.main(["--query", "data scientist", "--output", output, "--append"])
    assert exc.value.code == 0
    assert "Apple" in capsys.readouterr().out
    lines = open(output).readlines()
    assert len(lines) == 1


def test_cli_exits_1_when_all_scrapers_fail(tmp_path):
    output = str(tmp_path / "out.jsonl")

    def boom(self, query, limit=50):
        raise RuntimeError("upstream down")

    with patch.dict(cs.SCRAPERS, {"Amazon": AmazonScraperMock, "Apple": AppleScraperMock}):
        with patch.object(AmazonScraperMock, "fetch_jobs", boom), \
             patch.object(AppleScraperMock, "fetch_jobs", boom):
            with pytest.raises(SystemExit) as exc:
                cs.main(["--query", "data scientist", "--output", output, "--append"])
    assert exc.value.code == 1


def test_cli_dedupes_across_scrapers(tmp_path):
    output = str(tmp_path / "out.jsonl")

    shared_url = "https://amazon.jobs/j/1"
    rec_a = {"title": "DS", "company": "Amazon", "location": "X", "job_url": shared_url,
             "description": None, "date_posted": "2026-01-01", "job_type": None,
             "salary": None, "source": "amazon_career", "is_remote": None,
             "source_pass": "career_site", "source_company": "Amazon"}
    rec_b = {**rec_a, "source": "linkedin"}  # same job_url

    def fetch_a(self, query, limit=50):
        return [rec_a]
    def fetch_b(self, query, limit=50):
        return [rec_b]

    with patch.dict(cs.SCRAPERS, {"Amazon": AmazonScraperMock, "Apple": AppleScraperMock}):
        with patch.object(AmazonScraperMock, "fetch_jobs", fetch_a), \
             patch.object(AppleScraperMock, "fetch_jobs", fetch_b):
            with pytest.raises(SystemExit):
                cs.main(["--query", "data scientist", "--output", output, "--append"])

    lines = open(output).readlines()
    assert len(lines) == 1
