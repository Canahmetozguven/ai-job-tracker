import pytest
from scraper import deduplicate_jobs

def test_deduplicate_jobs():
    jobs = [
        {"job_url": "https://example.com/1", "title": "Job 1"},
        {"job_url": "https://example.com/1", "title": "Job 1 dup"},
        {"job_url": "https://example.com/2", "title": "Job 2"},
        {"job_url": None, "title": "Job 3"},
        {"job_url": None, "title": "Job 3 dup"},
    ]
    result = deduplicate_jobs(jobs)
    assert len(result) == 3
    assert result[0]["title"] == "Job 1"
    assert result[1]["title"] == "Job 2"
    assert result[2]["title"] == "Job 3"

def test_deduplicate_jobs_empty():
    result = deduplicate_jobs([])
    assert result == []

def test_deduplicate_jobs_all_same():
    jobs = [
        {"job_url": "https://example.com/1", "title": "Job 1"},
        {"job_url": "https://example.com/1", "title": "Job 1 dup"},
        {"job_url": "https://example.com/1", "title": "Job 1 dup 2"},
    ]
    result = deduplicate_jobs(jobs)
    assert len(result) == 1
    assert result[0]["title"] == "Job 1"

def test_deduplicate_jobs_no_url():
    jobs = [
        {"title": "Job 1"},
        {"title": "Job 2"},
    ]
    result = deduplicate_jobs(jobs)
    assert len(result) == 2