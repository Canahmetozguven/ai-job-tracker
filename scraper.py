#!/usr/bin/env python3
"""Job scraper CLI using JobSpy and LinkedIn-scraper."""

import asyncio
import json
import sys
from typing import Optional

try:
    from jobspy import scrape_jobs
    JOBSPY_AVAILABLE = True
except ImportError:
    JOBSPY_AVAILABLE = False

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

def run_menu() -> dict:
    """Run interactive menu, return config dict."""
    return {
        "query": prompt_search_query(),
        "location": prompt_location(),
        "source": prompt_source(),
        "limit": prompt_results_limit(),
        "output": prompt_output_file(),
    }

def scrape_with_jobspy(query: str, location: str, limit: int) -> list[dict]:
    """Scrape jobs using JobSpy."""
    if not JOBSPY_AVAILABLE:
        print("JobSpy not installed. Run: pip install python-jobspy")
        return []
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
    if df.empty:
        return []
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
            "is_remote": bool(row.get("is_remote")) if "is_remote" in row else None,
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

def main():
    """Entry point."""
    config = run_menu()
    if config["source"] in (1, 3):
        jobs = scrape_with_jobspy(config["query"], config["location"], config["limit"])
        print(f"JobSpy returned {len(jobs)} jobs")
    print(f"\nConfig: {config}")

if __name__ == "__main__":
    main()