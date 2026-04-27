#!/usr/bin/env python3
"""Job scraper + analyzer runner for cron jobs."""

import subprocess
import sys

def run_command(cmd: list, desc: str) -> bool:
    """Run a command and return success status."""
    print(f"=== {desc} ===")
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0

def main():
    print("Step 1: Scraping new jobs...")
    scrape_ok = run_command([
        sys.executable, "scraper.py",
        "--query", "data scientist",
        "--location", "Turkey",
        "--hours", "3",
        "--output", "jobs_linkedin.jsonl"
    ], "Scraping jobs")

    if not scrape_ok:
        print("Scraping failed, skipping analysis")
        sys.exit(1)

    print("\nStep 2: Analyzing new jobs...")
    run_command([
        sys.executable, "analyzer.py",
        "--jobs", "jobs_linkedin.jsonl",
        "--hours", "3",
        "--skip-seen"
    ], "Analyzing jobs")

    print("\nDone!")

if __name__ == "__main__":
    main()
