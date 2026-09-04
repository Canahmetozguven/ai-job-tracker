"""Tests for the career-site scraper core and its `job career` command."""

import datetime
import json
import sys
from unittest.mock import patch, MagicMock

import pytest

from typer.testing import CliRunner

from conftest import CLI_ENV, plain

from ai_job_tracker import career_scraper as cs
from ai_job_tracker.career_scrapers.base import BaseCareerScraper
from ai_job_tracker.cli import app


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


def test_career_help_shows_expected_flags():
    result = CliRunner(env=CLI_ENV).invoke(app, ["career", "--help"])
    assert result.exit_code == 0
    out = plain(result.output)
    for flag in ["--query", "--limit", "--hours", "--output", "--append", "--no-proxy", "--proxy"]:
        assert flag in out
    assert "no-op" not in out


def test_career_command_propagates_exit_code(tmp_path):
    """`job career` must surface run()'s exit code, not swallow it."""
    def boom(self, query, limit=50):
        raise RuntimeError("upstream down")

    with patch.dict(cs.SCRAPERS, {"Amazon": AmazonScraperMock, "Apple": AppleScraperMock}):
        with patch.object(AmazonScraperMock, "fetch_jobs", boom), \
             patch.object(AppleScraperMock, "fetch_jobs", boom):
            result = CliRunner(env=CLI_ENV).invoke(
                app, ["career", "--query", "ds", "--output", str(tmp_path / "o.jsonl")]
            )
    assert result.exit_code == 1


def test_career_requires_query():
    result = CliRunner(env=CLI_ENV).invoke(app, ["career", "--output", "x.jsonl"])
    assert result.exit_code != 0


@pytest.mark.parametrize(
    ("date_posted", "expected_to_keep"),
    [
        ("2026-09-03T12:00:00Z", True),
        ("2026-09-03T15:00:00+03:00", True),
        ("2026-09-03T12:00:00", True),
        ("2026-09-03", True),
        ("Sep 3, 2026", True),
        ("2026-09-04", True),
        ("Sep  4, 2026", True),
        ("2026-09-04T12:00:01Z", False),
        ("2026-09-05", False),
        ("Sep 5, 2026", False),
        ("2026-09-03T11:59:59Z", False),
        ("Sep  2, 2026", False),
        ("unknown", True),
        (None, True),
        ("not-a-date", True),
    ],
)
def test_filter_recent_jobs_handles_supported_date_representations(date_posted, expected_to_keep):
    current_time = datetime.datetime(2026, 9, 4, 12, tzinfo=datetime.UTC)
    job = {"job_url": "https://example.com/job", "date_posted": date_posted}

    filtered_jobs = cs.filter_recent_jobs([job], hours=24, current_time=current_time)

    assert bool(filtered_jobs) is expected_to_keep


def test_filter_recent_jobs_disables_filtering_when_hours_is_zero():
    old_job = {"job_url": "https://example.com/old", "date_posted": "Jan 1, 2000"}

    filtered_jobs = cs.filter_recent_jobs([old_job], hours=0)

    assert filtered_jobs == [old_job]


def test_amazon_dates_are_parsed_without_locale_sensitive_strptime(monkeypatch):
    class NoStrptimeDatetime(datetime.datetime):
        @classmethod
        def strptime(cls, date_string, date_format):
            raise AssertionError("locale-sensitive strptime must not parse Amazon dates")

    monkeypatch.setattr("ai_job_tracker.career_freshness.datetime.datetime", NoStrptimeDatetime)
    old_job = {"job_url": "https://example.com/old", "date_posted": "Jan 1, 2000"}
    current_time = datetime.datetime(2026, 9, 4, 12, tzinfo=datetime.UTC)

    filtered_jobs = cs.filter_recent_jobs([old_job], hours=24, current_time=current_time)

    assert filtered_jobs == []


def test_career_command_filters_old_jobs_using_hours(tmp_path):
    output_path = tmp_path / "jobs.jsonl"
    fetched_records = [
        {"job_url": "https://example.com/old", "date_posted": "Jan 1, 2000"},
        {"job_url": "https://example.com/unknown", "date_posted": "unknown"},
    ]

    with (
        patch.dict(cs.SCRAPERS, {"Amazon": AmazonScraperMock}),
        patch.object(AmazonScraperMock, "fetch_jobs", return_value=fetched_records),
    ):
        result = CliRunner(env=CLI_ENV).invoke(
            app,
            [
                "career",
                "--query",
                "data scientist",
                "--hours",
                "24",
                "--output",
                str(output_path),
                "--append",
            ],
        )

    written_urls = [json.loads(line)["job_url"] for line in output_path.read_text().splitlines()]
    assert result.exit_code == 0, plain(result.output)
    assert written_urls == ["https://example.com/unknown"]


def test_career_run_uses_one_reference_time_for_all_freshness_filters(tmp_path):
    reference_times = []
    boundary_job = {
        "job_url": "https://example.com/boundary",
        "date_posted": "Sep 4, 2026",
    }

    class ReferenceAwareScraper(AmazonScraperMock):
        def fetch_recent_jobs(self, query, limit=50, hours=0, *, current_time=None):
            reference_times.append(current_time)
            return cs.filter_recent_jobs([boundary_job], hours, current_time=current_time)

    current_time = datetime.datetime(2026, 9, 5, 0, 30, tzinfo=datetime.UTC)
    output_path = tmp_path / "jobs.jsonl"

    with patch.dict(cs.SCRAPERS, {"Amazon": ReferenceAwareScraper}):
        exit_code = cs.run(
            query="data scientist",
            hours=1,
            output=str(output_path),
            current_time=current_time,
        )

    written_urls = [json.loads(line)["job_url"] for line in output_path.read_text().splitlines()]
    assert exit_code == 0
    assert reference_times == [current_time]
    assert written_urls == ["https://example.com/boundary"]


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
            code = cs.run(query="data scientist", output=output, append=True)
    assert code == 0

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
            code = cs.run(query="data scientist", output=output, append=True)
    assert code == 0
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
            code = cs.run(query="data scientist", output=output, append=True)
    assert code == 1


def test_cli_exits_1_when_all_scrapers_return_empty(tmp_path):
    """Per spec: exit 1 if every scraper returned 0 records (no errors)."""
    output = str(tmp_path / "out.jsonl")

    def empty(self, query, limit=50):
        return []

    with patch.dict(cs.SCRAPERS, {"Amazon": AmazonScraperMock, "Apple": AppleScraperMock}):
        with patch.object(AmazonScraperMock, "fetch_jobs", empty), \
             patch.object(AppleScraperMock, "fetch_jobs", empty):
            code = cs.run(query="data scientist", output=output, append=True)
    assert code == 1


def test_cli_exits_1_when_some_error_and_others_empty(tmp_path):
    """Per spec: exit 1 when every scraper is in some failure state (error OR empty)."""
    output = str(tmp_path / "out.jsonl")

    def boom(self, query, limit=50):
        raise RuntimeError("upstream down")
    def empty(self, query, limit=50):
        return []

    with patch.dict(cs.SCRAPERS, {"Amazon": AmazonScraperMock, "Apple": AppleScraperMock}):
        with patch.object(AmazonScraperMock, "fetch_jobs", boom), \
             patch.object(AppleScraperMock, "fetch_jobs", empty):
            code = cs.run(query="data scientist", output=output, append=True)
    assert code == 1


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
            cs.run(query="data scientist", output=output, append=True)

    lines = open(output).readlines()
    assert len(lines) == 1
