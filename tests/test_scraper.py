import math
import pytest
from scraper import deduplicate_jobs, df_to_job_records, filter_big_tech, _clean

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


def test_clean_strips_nan_float():
    """Regression: NaN floats must become None so json.dumps stays valid."""
    assert _clean(float("nan")) is None
    assert _clean(None) is None
    assert _clean("hello") == "hello"
    assert _clean(42) == 42


def test_df_to_job_records_preserves_nan_date_as_string():
    """Regression: analyzer's recent filter relies on date_posted being a
    non-empty string for jobs whose date is unknown. A missing/NaN cell
    must become a non-empty, unparseable string so the filter's
    parse-failure fallback keeps the job."""
    class _Row(dict):
        def get(self, key, default=None):
            return super().get(key, default)

    df = type("DF", (), {"empty": False, "iterrows": lambda self: iter([(0, _Row({
        "title": "T", "company": "C", "location": "L", "job_url": "u",
        "description": None, "date_posted": float("nan"), "job_type": None,
        "min_amount": None, "max_amount": None, "currency": "USD",
        "site": "linkedin", "is_remote": False,
    }))])})()

    records = df_to_job_records(df, source_pass="turkey_local")
    assert len(records) == 1
    # The exact placeholder string isn't load-bearing — only that the
    # resulting value is a non-empty, non-parseable string so the analyzer
    # filter keeps the job.
    assert isinstance(records[0]["date_posted"], str)
    assert records[0]["date_posted"]  # non-empty
    assert records[0]["description"] is None
    assert records[0]["job_type"] is None
    assert records[0]["source_pass"] == "turkey_local"


def test_df_to_job_records_keeps_job_when_date_column_missing():
    """Regression: JobSpy sometimes omits date_posted entirely. The row
    accessor returns None for a missing key, which must not silently drop
    the job from the analyzer's recent filter."""
    class _Row(dict):
        def get(self, key, default=None):
            return super().get(key, default)

    df = type("DF", (), {"empty": False, "iterrows": lambda self: iter([(0, _Row({
        "title": "T", "company": "C", "location": "L", "job_url": "u",
        "description": None, "job_type": None,
        "min_amount": None, "max_amount": None, "currency": "USD",
        "site": "linkedin", "is_remote": False,
    }))])})()

    records = df_to_job_records(df, source_pass="turkey_local")
    assert len(records) == 1
    assert isinstance(records[0]["date_posted"], str) and records[0]["date_posted"]
    assert records[0]["source_pass"] == "turkey_local"


def test_df_to_job_records_handles_empty_dataframe():
    class _EmptyDF:
        empty = True
        def iterrows(self):
            return iter([])
    assert df_to_job_records(_EmptyDF(), source_pass="turkey_local") == []


def test_df_to_job_records_includes_source_pass():
    """Every record from df_to_job_records must carry the source_pass tag so
    downstream consumers (analyzer, Telegram summary) can distinguish Turkey-local
    jobs from Big Tech jobs."""
    class _Row(dict):
        def get(self, key, default=None):
            return super().get(key, default)

    df = type("DF", (), {"empty": False, "iterrows": lambda self: iter([(0, _Row({
        "title": "T", "company": "C", "location": "L", "job_url": "u",
        "description": None, "date_posted": "2026-01-01", "job_type": None,
        "min_amount": None, "max_amount": None, "currency": "USD",
        "site": "linkedin", "is_remote": False,
    }))])})()

    records = df_to_job_records(df, source_pass="turkey_local")
    assert len(records) == 1
    assert records[0]["source_pass"] == "turkey_local"

    records_bt = df_to_job_records(df, source_pass="big_tech_global")
    assert records_bt[0]["source_pass"] == "big_tech_global"


def test_filter_big_tech_keeps_matching_records():
    records = [
        {"title": "DS at Meta", "company": "Meta Platforms", "source_pass": "big_tech_global"},
        {"title": "DS at Apple", "company": "Apple Inc", "source_pass": "big_tech_global"},
        {"title": "DS at Random", "company": "Random Co", "source_pass": "big_tech_global"},
    ]
    kept = filter_big_tech(records)
    assert len(kept) == 2
    by_company = {r["company"]: r for r in kept}
    assert by_company["Meta Platforms"]["big_tech_company"] == "Meta"
    assert by_company["Apple Inc"]["big_tech_company"] == "Apple"


def test_filter_big_tech_drops_non_matches():
    records = [
        {"title": "DS at Acme", "company": "Acme Co"},
        {"title": "DS at Jobgether", "company": "Jobgether"},
    ]
    assert filter_big_tech(records) == []


def test_filter_big_tech_handles_none_company():
    records = [
        {"title": "DS at Unknown", "company": None},
        {"title": "DS at Meta", "company": "Meta"},
    ]
    kept = filter_big_tech(records)
    assert len(kept) == 1
    assert kept[0]["company"] == "Meta"


def test_filter_big_tech_handles_empty_company():
    records = [
        {"title": "DS at Empty", "company": ""},
        {"title": "DS at Google", "company": "Alphabet"},
    ]
    kept = filter_big_tech(records)
    assert len(kept) == 1
    assert kept[0]["big_tech_company"] == "Google"


def test_filter_big_tech_empty_input():
    assert filter_big_tech([]) == []