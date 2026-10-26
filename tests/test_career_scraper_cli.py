"""Tests for the career-site scraper core and its `job career` command."""

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
    ("append_arguments", "expected_titles"),
    [
        ([], ["Fresh result", "New result"]),
        (["--append"], ["Stored result", "New result"]),
    ],
)
def test_career_output_mode_matches_append_flag(tmp_path, append_arguments, expected_titles):
    output_path = tmp_path / "jobs-career.jsonl"
    output_path.write_text(
        json.dumps({"job_url": "https://existing.example/job", "title": "Stored result"}) + "\n"
    )
    fetched_records = [
        {"job_url": "https://existing.example/job", "title": "Fresh result"},
        {"job_url": "https://new.example/job", "title": "New result"},
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
                "--output",
                str(output_path),
                *append_arguments,
            ],
        )

    written_titles = [json.loads(line)["title"] for line in output_path.read_text().splitlines()]
    assert result.exit_code == 0, plain(result.output)
    assert written_titles == expected_titles


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


def test_career_without_append_clears_stale_output_when_no_jobs_are_found(tmp_path):
    output_path = tmp_path / "out.jsonl"
    output_path.write_text(json.dumps({"job_url": "https://stale.example/job"}) + "\n")

    with patch.dict(cs.SCRAPERS, {"Amazon": AmazonScraperMock}):
        exit_code = cs.run(query="data scientist", output=str(output_path), append=False)

    assert exit_code == 1
    assert output_path.read_text() == ""


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
