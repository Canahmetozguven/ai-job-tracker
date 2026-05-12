import json
import copy
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import pytest
import run_daily
from user_profile import load_profile
from job_loader import load_jobs, count_jobs
from analyzer import get_seen_urls
from analysis_validation import is_valid_analysis
from gemini_client import build_prompt, resolve_browser_executable
from analysis_summary import count_jsonl_lines, read_jsonl_records, summarize_analysis_results
from telegram_notify import format_job_analysis, format_run_summary, parse_gemini_response

def test_load_profile(tmp_path):
    """Test profile loading."""
    p = tmp_path / "profile.txt"
    p.write_text("Python developer with 5 years experience")
    assert load_profile(str(p)) == "Python developer with 5 years experience"

def test_load_profile_empty(tmp_path):
    """Test empty profile raises error? Or returns empty string?"""
    p = tmp_path / "profile.txt"
    p.write_text("")
    # Empty profile is still valid
    assert load_profile(str(p)) == ""

def test_load_jobs_single(tmp_path):
    """Test loading single job."""
    f = tmp_path / "jobs.jsonl"
    f.write_text('{"title": "Dev", "company": "Acme"}')
    jobs = list(load_jobs(str(f)))
    assert len(jobs) == 1
    assert jobs[0]['title'] == 'Dev'

def test_load_jobs_multiple(tmp_path):
    """Test loading multiple jobs."""
    f = tmp_path / "jobs.jsonl"
    f.write_text('{"title": "Dev", "company": "Acme"}\n{"title": "Eng", "company": "Beta"}')
    jobs = list(load_jobs(str(f)))
    assert len(jobs) == 2
    assert jobs[0]['title'] == 'Dev'
    assert jobs[1]['title'] == 'Eng'

def test_load_jobs_ignores_invalid_json(tmp_path):
    """Test that invalid JSON lines are skipped."""
    f = tmp_path / "jobs.jsonl"
    f.write_text('{"title": "Dev"}\ninvalid json\n{"title": "Eng"}')
    jobs = list(load_jobs(str(f)))
    assert len(jobs) == 2

def test_count_jobs(tmp_path):
    """Test job counting."""
    f = tmp_path / "jobs.jsonl"
    f.write_text('{"title": "Dev"}\n{"title": "Eng"}\n{"title": "QA"}')
    assert count_jobs(str(f)) == 3

def test_parse_gemini_response_complete():
    """Test parsing a complete Gemini response."""
    text = """1. FIT SCORE: 8/10
2. WHY GOOD: Great match for my Python skills
3. WHY BAD: Salary is below my期望
4. RECOMMENDATION: Apply"""
    result = parse_gemini_response(text)
    assert result['score'] == '8/10'
    assert 'Python skills' in result['why_good']
    assert 'Salary' in result['why_bad']
    assert result['recommendation'] == 'Apply'


def test_parse_gemini_response_preserves_recommendation_next_step():
    text = """FIT SCORE: 8/10
WHY GOOD: Strong Python match
WHY BAD: Confirm salary
RECOMMENDATION: apply — tailor resume to Django and AWS"""

    result = parse_gemini_response(text)

    assert result['recommendation'] == 'Apply — tailor resume to Django and AWS'
    assert is_valid_analysis(result)

def test_parse_gemini_response_partial():
    """Test parsing response with missing fields."""
    text = """1. FIT SCORE: 7/10
3. WHY BAD: Not a good fit"""
    result = parse_gemini_response(text)
    assert result['score'] == '7/10'
    assert result['why_good'] == 'N/A'
    assert 'Not a good fit' in result['why_bad']

def test_format_job_analysis():
    """Test formatting job analysis as Telegram message."""
    job = {
        'title': 'Senior Python Developer',
        'company': 'TechCorp',
        'location': 'San Francisco, CA',
        'job_url': 'https://example.com/job/123'
    }
    analysis = {
        'score': '9/10',
        'why_good': 'Perfect match for my Django and AWS experience',
        'why_bad': 'Might be too senior for my level',
        'recommendation': 'Apply'
    }
    msg = format_job_analysis(job, analysis)

    assert 'Senior Python Developer' in msg
    assert 'TechCorp' in msg
    assert 'San Francisco' in msg
    assert '9/10' in msg
    assert 'Django and AWS' in msg
    assert 'Apply' in msg


def test_build_prompt_uses_actionable_shortlist_guidance():
    prompt = build_prompt(
        'Python developer with AWS and Django experience',
        {
            'title': 'Senior Python Engineer',
            'company': 'Acme',
            'location': 'Remote',
            'job_url': 'https://example.com/job/1',
            'description': 'Build APIs with Python, Django, and AWS.',
        },
    )

    assert 'FIT SCORE:' in prompt
    assert 'WHY GOOD:' in prompt
    assert 'WHY BAD:' in prompt
    assert 'RECOMMENDATION:' in prompt
    assert 'actionable shortlist' in prompt.lower()
    assert 'strict' in prompt.lower()
    assert 'dealbreakers' in prompt.lower()
    assert 'risks' in prompt.lower()
    assert 'next step' in prompt.lower()
    assert 'RECOMMENDATION: <Apply|Review|Skip> — <one short next step>' in prompt
    assert 'Apply | Review | Skip' not in prompt


def test_build_prompt_truncates_description_to_2000_chars():
    prompt = build_prompt(
        'Profile',
        {
            'title': 'Role',
            'company': 'Company',
            'location': 'Remote',
            'job_url': 'https://example.com/job/2',
            'description': '~' * 2500,
        },
    )

    assert prompt.count('~') == 2000


def test_get_seen_urls_only_includes_successful_analysis_records(tmp_path):
    results = tmp_path / "analysis_results.jsonl"
    results.write_text(
        json.dumps({
            "job": {"job_url": "https://success.example/job-1"},
            "analysis": {"score": "8/10", "recommendation": "Apply"},
        })
        + "\n"
        + json.dumps({
            "job": {"job_url": "https://failed.example/job-2"},
            "error": "Gemini failed after 3 attempts",
        })
        + "\n"
        + json.dumps({
            "job": {"job_url": "https://missing-analysis.example/job-3"},
        })
        + "\n"
        + json.dumps({
            "job": {"job_url": "https://invalid-analysis.example/job-4"},
            "analysis": {"score": "N/A", "recommendation": "N/A"},
        })
        + "\n"
    )

    assert get_seen_urls(str(results)) == {"https://success.example/job-1"}


def test_is_valid_analysis_requires_score_and_recommendation():
    assert is_valid_analysis({"score": "8/10", "recommendation": "Review — confirm salary"})
    assert is_valid_analysis({"score": "8/10", "recommendation": "apply — tailor resume"})
    assert not is_valid_analysis({"score": "N/A", "recommendation": "Apply"})
    assert not is_valid_analysis({"score": "8/10", "recommendation": "N/A"})
    assert not is_valid_analysis({"score": "8/10", "recommendation": "Maybe"})
    assert not is_valid_analysis({"score": "8/10", "recommendation": "Apply | Review | Skip"})


def test_summarize_analysis_results_handles_no_jobs_and_partial_and_failed():
    no_jobs = summarize_analysis_results([], analyzer_ok=True)
    assert no_jobs["status"] == "no_jobs"
    assert no_jobs["processed"] == 0
    assert no_jobs["succeeded"] == 0
    assert no_jobs["failed"] == 0

    partial = summarize_analysis_results(
        [
            {"job": {"job_url": "https://success.example/job"}, "analysis": {"score": "9/10", "recommendation": "Apply"}},
            {"job": {"job_url": "https://failed.example/job"}, "error": "Gemini failed after 3 attempts: browser not found"},
            {"job": {"job_url": "https://invalid.example/job"}, "analysis": {"score": "N/A", "recommendation": "N/A"}},
        ],
        analyzer_ok=True,
    )
    assert partial["status"] == "partial"
    assert partial["processed"] == 3
    assert partial["succeeded"] == 1
    assert partial["failed"] == 2
    assert partial["error_summary"] == (
        "2 of 3 jobs failed. First error: Gemini failed after 3 attempts: browser not found"
    )

    failed = summarize_analysis_results(
        [
            {"job": {"job_url": "https://failed.example/job-1"}, "error": "Gemini failed after 3 attempts: executable doesn't exist"},
            {"job": {"job_url": "https://failed.example/job-2"}, "error": "Gemini failed after 3 attempts: executable doesn't exist"},
        ],
        analyzer_ok=True,
    )
    assert failed["status"] == "failed"
    assert failed["processed"] == 2
    assert failed["succeeded"] == 0
    assert failed["failed"] == 2
    assert failed["error_summary"].startswith("All 2 jobs failed.")
    assert "executable doesn't exist" in failed["error_summary"]


def test_resolve_browser_executable_accepts_explicit_browser_command(monkeypatch):
    monkeypatch.setattr("gemini_client.shutil.which", lambda command: "/usr/bin/brave-browser" if command == "brave-browser" else None)

    assert resolve_browser_executable("brave-browser") == "/usr/bin/brave-browser"


def test_resolve_browser_executable_accepts_explicit_executable_path(tmp_path):
    executable = tmp_path / "browser-bin"
    executable.write_text("#!/bin/sh\nexit 0\n")
    executable.chmod(0o755)

    assert resolve_browser_executable(str(executable)) == str(executable)


def test_resolve_browser_executable_returns_none_by_default_for_automation(monkeypatch):
    """Without an explicit browser, resolver returns None so Playwright uses bundled Chromium.

    External browsers (Brave, Chrome) often lack headless-mode support and are not
    recommended for automated Gemini interaction.
    """
    monkeypatch.setattr(
        "gemini_client.shutil.which",
        lambda command: "/usr/bin/brave-origin-nightly" if command == "brave-origin-nightly" else None,
    )

    assert resolve_browser_executable() is None


def test_resolve_browser_executable_rejects_missing_explicit_command(monkeypatch):
    monkeypatch.setattr("gemini_client.shutil.which", lambda command: None)

    with pytest.raises(FileNotFoundError, match="missing-browser"):
        resolve_browser_executable("missing-browser")


def test_resolve_browser_executable_rejects_missing_explicit_path(tmp_path):
    missing = tmp_path / "does-not-exist"
    with pytest.raises(FileNotFoundError):
        resolve_browser_executable(str(missing))


def test_resolve_browser_executable_returns_none_without_browser_on_path(monkeypatch):
    monkeypatch.setattr("gemini_client.shutil.which", lambda command: None)

    assert resolve_browser_executable() is None


def test_gitignore_includes_runtime_artifact_exclusions():
    gitignore = Path(__file__).resolve().parents[1] / ".gitignore"
    lines = set(gitignore.read_text().splitlines())

    assert {
        "analysis_results.jsonl",
        "jobs_linkedin.jsonl",
        "USER_INFO_BACKUP_DESKTOP-MR1KOEH/",
    }.issubset(lines)


def test_count_jsonl_lines_and_read_jsonl_records_with_start_index(tmp_path):
    path = tmp_path / "analysis_results.jsonl"
    path.write_text(
        json.dumps({"job": {"job_url": "https://job-1.example"}})
        + "\n"
        + json.dumps({"job": {"job_url": "https://job-2.example"}})
        + "\n"
        + "not json\n"
        + json.dumps({"job": {"job_url": "https://job-3.example"}})
        + "\n"
    )

    assert count_jsonl_lines(str(path)) == 4
    assert read_jsonl_records(str(path), start_index=2) == [
        {"job": {"job_url": "https://job-3.example"}},
    ]


def test_format_run_summary_handles_no_jobs_and_partial():
    summary = {
        "proxy_validation": {"working": 1, "total": 1, "selected": "127.0.0.1:8080"},
        "scrape": {"status": "success", "found": 5, "new": 1},
        "analyze": {"status": "no_jobs", "processed": 0, "succeeded": 0, "failed": 0, "error_summary": None},
        "errors": [],
    }

    no_jobs_message = format_run_summary(summary)
    assert "Status: NO_JOBS" in no_jobs_message
    assert "No new jobs to analyze" in no_jobs_message
    assert "cron is still running" in no_jobs_message
    assert "✅ *SUCCESS*" in no_jobs_message

    summary["analyze"] = {
        "status": "partial",
        "processed": 2,
        "succeeded": 1,
        "failed": 1,
        "error_summary": "All 1 jobs failed. First error: Gemini failed after 3 attempts: browser not found",
    }
    partial_message = format_run_summary(summary)
    assert "Status: PARTIAL" in partial_message
    assert "❌ *ISSUES DETECTED*" in partial_message


def test_format_run_summary_marks_failed_analysis_as_issues():
    summary = {
        "proxy_validation": {"working": 1, "total": 1, "selected": None},
        "scrape": {"status": "success", "found": 1, "new": 1},
        "analyze": {"status": "failed", "processed": 1, "succeeded": 0, "failed": 1, "error_summary": "All 1 jobs failed. First error: boom"},
        "errors": ["All 1 jobs failed. First error: boom"],
    }

    msg = format_run_summary(summary)
    assert "Status: FAILED" in msg
    assert "❌ *ISSUES DETECTED*" in msg


def test_print_summary_marks_partial_analysis_as_issues_detected_and_partial_status():
    original_run_summary = copy.deepcopy(run_daily.run_summary)
    run_daily.run_summary = {
        "started_at": None,
        "proxy_validation": {"total": 1, "working": 1, "selected": "127.0.0.1:8080"},
        "scrape": {"found": 2, "new": 2, "status": "success"},
        "analyze": {
            "processed": 2,
            "succeeded": 1,
            "failed": 1,
            "status": "partial",
            "error_summary": "1 of 2 jobs failed. First error: boom",
        },
        "errors": [],
    }

    try:
        buffer = StringIO()
        with redirect_stdout(buffer):
            run_daily.print_summary(send_tg=False)
        output = buffer.getvalue()

        assert "Status:      PARTIAL" in output
        assert "OVERALL: ISSUES DETECTED" in output
    finally:
        run_daily.run_summary = original_run_summary
