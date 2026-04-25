# Job Scraper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** CLI tool that scrapes jobs via JobSpy (primary) and linkedin-scraper (fallback), outputs to JSON Lines format

**Architecture:** Single `scraper.py` with interactive CLI menu, uses asyncio for LinkedIn scraper and sync calls for JobSpy, deduplicates by job_url before output

**Tech Stack:** Python 3.10+, python-jobspy, linkedin-scraper v3.x, Playwright

---

## File Structure

```
job_scraper/
├── scraper.py          # Main CLI with menu and scraping logic
├── requirements.txt    # Dependencies
├── session.json        # (user-created, LinkedIn auth)
├── jobs.jsonl           # Output file (default)
└── tests/
    └── test_scraper.py  # Unit tests
```

---

## Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `scraper.py` (stub with imports)

- [ ] **Step 1: Create requirements.txt**

```
python-jobspy>=1.0.0
linkedin-scraper>=3.0.0
playwright
```

- [ ] **Step 2: Create scraper.py with imports and stub main**

```python
#!/usr/bin/env python3
"""Job scraper CLI using JobSpy and LinkedIn-scraper."""

import asyncio
import json
import sys
from typing import Optional

def main():
    """Entry point."""
    print("Job Scraper CLI")

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Verify syntax**

Run: `python3 -m py_compile scraper.py`
Expected: No output (success)

- [ ] **Step 4: Commit**

```bash
git init
git add requirements.txt scraper.py
git commit -m "feat: initial project setup"
```

---

## Task 2: CLI Menu

**Files:**
- Modify: `scraper.py` (add menu functions)

- [ ] **Step 1: Add CLI menu functions**

```python
def prompt_search_query() -> str:
    """Prompt for job search query."""
    return input("Enter job search query: ").strip()

def prompt_location() -> str:
    """Prompt for location."""
    return input("Enter location (city, state/country): ").strip()

def prompt_source() -> int:
    """Prompt for source selection."""
    print("\nSelect source:")
    print("  [1] JobSpy only (default)")
    print("  [2] LinkedIn-scraper only")
    print("  [3] Both with fallback (JobSpy → LinkedIn)")
    while True:
        choice = input("Choice [1]: ").strip() or "1"
        if choice in ("1", "2", "3"):
            return int(choice)
        print("Invalid choice, please enter 1, 2, or 3")

def prompt_results_limit() -> int:
    """Prompt for results limit per source."""
    while True:
        limit = input("Results limit per source [10]: ").strip() or "10"
        try:
            n = int(limit)
            if n > 0:
                return n
        except ValueError:
            pass
        print("Please enter a positive number")

def prompt_output_file() -> str:
    """Prompt for output file path."""
    return input("Output file [jobs.jsonl]: ").strip() or "jobs.jsonl"
```

- [ ] **Step 2: Add run_menu() that calls all prompts**

```python
def run_menu() -> dict:
    """Run interactive menu, return config dict."""
    return {
        "query": prompt_search_query(),
        "location": prompt_location(),
        "source": prompt_source(),
        "limit": prompt_results_limit(),
        "output": prompt_output_file(),
    }
```

- [ ] **Step 3: Update main() to call run_menu() and print config**

```python
def main():
    config = run_menu()
    print(f"\nConfig: {config}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Test menu interaction**

Run: `echo -e "Software Engineer\nSan Francisco\n\n\n\n" | python3 scraper.py`
Expected: prints config with default values used

- [ ] **Step 5: Commit**

```bash
git add scraper.py
git commit -m "feat: add interactive CLI menu"
```

---

## Task 3: JobSpy Integration

**Files:**
- Modify: `scraper.py` (add scrape_with_jobspy function)

- [ ] **Step 1: Add scrape_with_jobspy function**

```python
from jobspy import scrape_jobs

def scrape_with_jobspy(query: str, location: str, limit: int) -> list[dict]:
    """Scrape jobs using JobSpy."""
    print(f"\nScraping with JobSpy: '{query}' in '{location}'...")
    try:
        df = scrape_jobs(
            site_name=["indeed", "linkedin", "zip_recruiter", "google"],
            search_term=query,
            location=location,
            results_wanted=limit,
            verbose=1,
        )
        print(f"  Found {len(df)} jobs")
        return df_to_job_records(df)
    except Exception as e:
        print(f"  JobSpy error: {e}")
        return []

def df_to_job_records(df) -> list[dict]:
    """Convert pandas DataFrame to list of job dicts."""
    records = []
    for _, row in df.iterrows():
        record = {
            "title": row.get("title"),
            "company": row.get("company"),
            "location": row.get("location"),
            "job_url": row.get("job_url"),
            "description": row.get("description"),
            "date_posted": str(row.get("date_posted", "")),
            "job_type": row.get("job_type"),
            "salary": None,
            "source": row.get("site_name", "unknown"),
            "is_remote": bool(row.get("is_remote")),
        }
        # Handle salary if present
        if row.get("min_amount") or row.get("max_amount"):
            record["salary"] = {
                "min": row.get("min_amount"),
                "max": row.get("max_amount"),
                "currency": row.get("currency", "USD"),
            }
        records.append(record)
    return records
```

- [ ] **Step 2: Update main() to call scrape_with_jobspy**

```python
def main():
    config = run_menu()
    if config["source"] in (1, 3):
        jobs = scrape_with_jobspy(config["query"], config["location"], config["limit"])
        print(f"JobSpy returned {len(jobs)} jobs")
```

- [ ] **Step 3: Test (may need pip install)**

Run: `pip install -q python-jobspy pandas && echo -e "software\nsf\n1\n5\ntest.jsonl\n" | python3 scraper.py`
Expected: prints job count (actual jobs or 0)

- [ ] **Step 4: Commit**

```bash
git add scraper.py
git commit -m "feat: integrate JobSpy scraper"
```

---

## Task 4: LinkedIn-Scraper Integration (Fallback)

**Files:**
- Modify: `scraper.py` (add scrape_with_linkedin function)

- [ ] **Step 1: Add LinkedIn scrape function**

```python
import asyncio
from linkedin_scraper import BrowserManager, JobSearchScraper

async def scrape_with_linkedin(query: str, location: str, limit: int) -> list[dict]:
    """Scrape jobs using LinkedIn-scraper (async)."""
    print(f"\nScraping with LinkedIn-scraper: '{query}' in '{location}'...")
    try:
        async with BrowserManager() as browser:
            # Check for session file
            import os
            if not os.path.exists("session.json"):
                print("  No session.json found, skipping LinkedIn")
                return []
            await browser.load_session("session.json")
            scraper = JobSearchScraper(browser.page)
            jobs = await scraper.search(
                keywords=query,
                location=location,
                limit=limit,
            )
            print(f"  Found {len(jobs)} jobs")
            return linkedin_jobs_to_records(jobs)
    except Exception as e:
        print(f"  LinkedIn error: {e}")
        return []

def linkedin_jobs_to_records(jobs) -> list[dict]:
    """Convert LinkedIn Job objects to records."""
    records = []
    for job in jobs:
        record = {
            "title": getattr(job, "title", None),
            "company": getattr(job, "company", None),
            "location": getattr(job, "location", None),
            "job_url": getattr(job, "linkedin_url", None),
            "description": getattr(job, "description", None),
            "date_posted": None,
            "job_type": getattr(job, "employment_type", None),
            "salary": None,
            "source": "linkedin",
            "is_remote": None,
        }
        records.append(record)
    return records
```

- [ ] **Step 2: Update main() to support fallback**

```python
async def main_async(config):
    jobs = []
    if config["source"] in (1, 3):
        jobs = scrape_with_jobspy(config["query"], config["location"], config["limit"])
    # Fallback if source is 2, or if JobSpy returned <5 jobs and source is 3
    if config["source"] == 2 or (config["source"] == 3 and len(jobs) < 5):
        linkedin_jobs = await scrape_with_linkedin(config["query"], config["location"], config["limit"])
        jobs.extend(linkedin_jobs)
    # Deduplicate by job_url
    jobs = deduplicate_jobs(jobs)
    # Write output
    write_jobs_jsonl(jobs, config["output"])
    print(f"\nTotal: {len(jobs)} unique jobs written to {config['output']}")

def deduplicate_jobs(jobs: list[dict]) -> list[dict]:
    """Deduplicate by job_url."""
    seen = set()
    result = []
    for job in jobs:
        url = job.get("job_url")
        if url and url not in seen:
            seen.add(url)
            result.append(job)
    return result

def write_jobs_jsonl(jobs: list[dict], output_path: str):
    """Write jobs to JSON Lines file."""
    with open(output_path, "w") as f:
        for job in jobs:
            f.write(json.dumps(job) + "\n")
```

- [ ] **Step 3: Update main() to call main_async**

```python
def main():
    config = run_menu()
    asyncio.run(main_async(config))
```

- [ ] **Step 4: Commit**

```bash
git add scraper.py
git commit -m "feat: add LinkedIn-scraper fallback"
```

---

## Task 5: Tests

**Files:**
- Create: `tests/test_scraper.py`

- [ ] **Step 1: Write unit tests**

```python
import pytest
from scraper import deduplicate_jobs, df_to_job_records

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

def test_df_to_job_records_empty():
    import pandas as pd
    df = pd.DataFrame(columns=["title", "company"])
    result = df_to_job_records(df)
    assert result == []

def test_df_to_job_records_with_data():
    import pandas as pd
    df = pd.DataFrame([{
        "title": "Engineer",
        "company": "Acme",
        "location": "NYC",
        "job_url": "https://example.com",
        "description": "Build things",
        "date_posted": "2026-04-25",
        "job_type": "fulltime",
        "min_amount": 100000,
        "max_amount": 150000,
        "currency": "USD",
        "site_name": "indeed",
        "is_remote": False,
    }])
    result = df_to_job_records(df)
    assert len(result) == 1
    assert result[0]["title"] == "Engineer"
    assert result[0]["salary"]["min"] == 100000
    assert result[0]["source"] == "indeed"
```

- [ ] **Step 2: Run tests**

Run: `pip install pytest pandas && python -m pytest tests/test_scraper.py -v`
Expected: 3 tests pass

- [ ] **Step 3: Commit**

```bash
git add tests/test_scraper.py
git commit -m "test: add unit tests for scraper"
```

---

## Task 6: Final Integration Test

- [ ] **Step 1: Run full script with test inputs**

Run: `echo -e "python developer\nsan francisco\n1\n3\ntest_output.jsonl\n" | python3 scraper.py`
Expected: completes without error, creates output file

- [ ] **Step 2: Verify JSON Lines output**

Run: `head -1 test_output.jsonl | python -m json.tool`
Expected: valid JSON with expected fields

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat: complete job scraper with JobSpy and LinkedIn fallback"
```

---

## Execution Options

**Plan complete and saved to `docs/superpowers/plans/2026-04-25-job-scraper-plan.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**