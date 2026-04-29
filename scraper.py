#!/usr/bin/env python3
"""Job scraper CLI using JobSpy and LinkedIn-scraper with scheduled mode."""

import argparse
import asyncio
import json
import os
import random
import sys
import time
from datetime import datetime
from typing import Optional

try:
    from jobspy import scrape_jobs
    JOBSPY_AVAILABLE = True
except ImportError:
    JOBSPY_AVAILABLE = False

try:
    from linkedin_scraper import BrowserManager, JobSearchScraper
    LINKEDIN_AVAILABLE = True
except ImportError:
    LINKEDIN_AVAILABLE = False

PROXY_FILE = "proxies/working.txt"

def load_proxies(path: str) -> list[str]:
    """Load proxies from file, returns list of 'host:port' strings."""
    if not os.path.exists(path):
        print(f"  Warning: proxy file not found at {path}")
        return []
    with open(path) as f:
        return [line.strip() for line in f if line.strip() and ":" in line]

def get_random_proxy(proxies: list[str]) -> str | None:
    """Return a random proxy or None if list is empty."""
    return random.choice(proxies) if proxies else None

def scrape_with_jobspy(query: str, location: str, limit: int, hours_old: int = 0, proxy: str = None) -> list[dict]:
    """Scrape jobs using JobSpy. hours_old filters by freshness (0=disabled). Proxy is optional."""
    if not JOBSPY_AVAILABLE:
        print("JobSpy not installed. Run: pip install python-jobspy")
        return []
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Scraping with JobSpy: '{query}' in '{location}'...")
    kwargs = {
        "site_name": ["indeed", "linkedin", "zip_recruiter", "google"],
        "search_term": query,
        "location": location,
        "results_wanted": limit,
        "verbose": 1,
    }
    if hours_old > 0:
        kwargs["hours_old"] = hours_old
        print(f"  Filter: jobs posted in last {hours_old} hour(s)")
    if proxy:
        kwargs["proxy"] = proxy
        print(f"  Using proxy: {proxy}")
    try:
        df = scrape_jobs(**kwargs)
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
        if row.get("min_amount") or row.get("max_amount"):
            record["salary"] = {
                "min": row.get("min_amount"),
                "max": row.get("max_amount"),
                "currency": row.get("currency", "USD"),
            }
        records.append(record)
    return records

async def scrape_with_linkedin(query: str, location: str, limit: int) -> list[dict]:
    """Scrape jobs using LinkedIn-scraper (async)."""
    if not LINKEDIN_AVAILABLE:
        print("LinkedIn-scraper not installed. Run: pip install linkedin-scraper")
        return []
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Scraping with LinkedIn-scraper: '{query}' in '{location}'...")
    try:
        async with BrowserManager() as browser:
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

def deduplicate_jobs(jobs: list[dict]) -> list[dict]:
    """Deduplicate by job_url while keeping no-URL jobs when needed."""
    seen = set()
    result = []
    has_url_jobs = any(job.get("job_url") for job in jobs)
    seen_no_url = False

    for job in jobs:
        url = job.get("job_url")
        if url:
            if url in seen:
                continue
            seen.add(url)
            result.append(job)
            continue

        if has_url_jobs:
            if seen_no_url:
                continue
            seen_no_url = True

        result.append(job)

    return result

def read_existing_jobs(output_path: str) -> set:
    """Read existing job URLs from output file."""
    seen = set()
    if os.path.exists(output_path):
        with open(output_path) as f:
            for line in f:
                try:
                    job = json.loads(line)
                    if job.get("job_url"):
                        seen.add(job["job_url"])
                except json.JSONDecodeError:
                    continue
    return seen

def append_jobs_jsonl(jobs: list[dict], output_path: str, existing_urls: set):
    """Append new jobs to JSON Lines file, skipping duplicates."""
    count = 0
    with open(output_path, "a") as f:
        for job in jobs:
            url = job.get("job_url")
            if url and url not in existing_urls:
                f.write(json.dumps(job) + "\n")
                existing_urls.add(url)
                count += 1
    return count

async def run_scrape(config: dict, proxy: str = None):
    """Run a single scrape cycle. Uses hours_old filter to get fresh jobs."""
    hours_old = config.get("hours_old", 0)
    jobs = []
    if config["source"] in (1, 3):
        jobs = scrape_with_jobspy(config["query"], config["location"], config["limit"], hours_old, proxy)
    if config["source"] == 2 or (config["source"] == 3 and len(jobs) < 5):
        linkedin_jobs = await scrape_with_linkedin(config["query"], config["location"], config["limit"])
        jobs.extend(linkedin_jobs)
    jobs = deduplicate_jobs(jobs)
    return jobs

async def run_daemon(config: dict, proxy: str = None):
    """Run scraper in daemon mode at specified interval."""
    interval_seconds = config["interval"] * 60
    print(f"Starting daemon mode - scraping every {config['interval']} minutes")
    print(f"Output file: {config['output']}")
    print(f"Query: {config['query']} in {config['location']}")
    print(f"Sources: {config['source']}")
    if proxy:
        print(f"Proxy: {proxy}")
    print("Press Ctrl+C to stop\n")

    count_total = 0
    count_all = 0
    existing_urls = read_existing_jobs(config["output"])

    while True:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cycle_proxy = get_random_proxy(proxies) if proxies else None
        if cycle_proxy:
            print(f"[{timestamp}] Using proxy: {cycle_proxy}")
        print(f"\n{'='*50}")
        print(f"[{timestamp}] Starting scrape cycle...")
        jobs = await run_scrape(config, cycle_proxy)
        new_count = append_jobs_jsonl(jobs, config["output"], existing_urls)
        count_total += new_count
        count_all += len(jobs)
        print(f"[{timestamp}] Cycle complete: {new_count} new ({len(jobs)} total), {count_total} cumulative")
        print(f"Next scrape in {config['interval']} minutes...")
        await asyncio.sleep(interval_seconds)

def main():
    parser = argparse.ArgumentParser(description="Job scraper with scheduled mode")
    parser.add_argument("--query", "-q", help="Job search query")
    parser.add_argument("--location", "-l", help="Location (city, state/country)")
    parser.add_argument("--source", "-s", type=int, default=1, choices=[1, 2, 3],
                        help="1=JobSpy only, 2=LinkedIn only, 3=Both with fallback")
    parser.add_argument("--limit", "-n", type=int, default=10, help="Results limit per source")
    parser.add_argument("--output", "-o", default="jobs.jsonl", help="Output file path")
    parser.add_argument("--daemon", "-d", action="store_true", help="Run continuously")
    parser.add_argument("--interval", "-i", type=int, default=30, help="Interval in minutes (daemon mode)")
    parser.add_argument("--hours", "-H", type=int, default=0, help="Filter jobs posted in last N hours (0=disabled)")
    parser.add_argument("--append", "-a", action="store_true", help="Append to output file (don't overwrite)")
    parser.add_argument("--no-proxy", action="store_true", help="Disable proxy rotation")
    parser.add_argument("--proxy", help="Use a specific proxy instead of random")

    args = parser.parse_args()

    # Interactive mode if no args provided
    if len(sys.argv) == 1:
        query = input("Enter job search query: ").strip()
        location = input("Enter location (city, state/country): ").strip()
        print("\nSelect source:")
        print("  [1] JobSpy only (default)")
        print("  [2] LinkedIn-scraper only")
        print("  [3] Both with fallback (JobSpy → LinkedIn)")
        while True:
            choice = input("Choice [1]: ").strip() or "1"
            if choice in ("1", "2", "3"):
                source = int(choice)
                break
            print("Invalid choice")
        limit = 10
        while True:
            limit_str = input("Results limit per source [10]: ").strip() or "10"
            try:
                limit = int(limit_str)
                if limit > 0:
                    break
            except ValueError:
                pass
            print("Please enter a positive number")
        output = input("Output file [jobs.jsonl]: ").strip() or "jobs.jsonl"
        append_mode = input("Append to file? [y/N]: ").strip().lower() == "y"
        interval = 30
        daemon = input("Run continuously? [y/N]: ").strip().lower() == "y"
        if daemon:
            while True:
                interval_str = input("Interval in minutes [30]: ").strip() or "30"
                try:
                    interval = int(interval_str)
                    if interval > 0:
                        break
                except ValueError:
                    pass
    else:
        query = args.query or input("Enter job search query: ").strip() if not args.query else args.query
        location = args.location or input("Enter location (city, state/country): ").strip() if not args.location else args.location
        source = args.source
        limit = args.limit
        output = args.output
        append_mode = args.append
        daemon = args.daemon
        interval = args.interval
        hours_old = args.hours
        no_proxy = args.no_proxy
        specific_proxy = args.proxy

    # Load proxies
    proxies = [] if no_proxy else load_proxies(PROXY_FILE)
    if proxies:
        print(f"Loaded {len(proxies)} proxies from {PROXY_FILE}")
    else:
        print("No proxies loaded (using direct connection)")

    # Determine proxy for this run
    run_proxy = specific_proxy if specific_proxy else (random.choice(proxies) if proxies else None)
    if run_proxy:
        print(f"Using proxy: {run_proxy}")

    config = {
        "query": query,
        "location": location,
        "source": source,
        "limit": limit,
        "output": output,
        "interval": interval,
        "hours_old": hours_old,
    }

    if append_mode and os.path.exists(output):
        existing = read_existing_jobs(output)
        print(f"Resuming with {len(existing)} existing jobs loaded")

    if daemon:
        asyncio.run(run_daemon(config, run_proxy))
    else:
        async def run_once():
            existing_urls = read_existing_jobs(config["output"])
            jobs = await run_scrape(config, run_proxy)
            new_count = append_jobs_jsonl(jobs, config["output"], existing_urls)
            print(f"Wrote {new_count} new jobs to {config['output']}")
        asyncio.run(run_once())

if __name__ == "__main__":
    main()
