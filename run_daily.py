#!/usr/bin/env python3
"""Job scraper + analyzer runner for cron jobs with retry support."""

import os
import random
import subprocess
import sys
import time

MAX_RETRIES = 3
RETRY_DELAY = 30  # seconds between retries
PROXY_FILE = "proxies/working.txt"

def load_proxies(path: str) -> list[str]:
    """Load proxies from file."""
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [line.strip() for line in f if line.strip() and ":" in line]

def run_command(cmd: list, desc: str, retries: int = MAX_RETRIES) -> bool:
    """Run a command with retry support."""
    for attempt in range(retries):
        print(f"=== {desc} (attempt {attempt + 1}/{retries}) ===")
        result = subprocess.run(cmd, capture_output=False)
        if result.returncode == 0:
            return True
        if attempt < retries - 1:
            print(f"Failed, retrying in {RETRY_DELAY}s...")
            time.sleep(RETRY_DELAY)
    return False

def main():
    print("Step 1: Scraping new jobs (last 1 hour)...")

    proxies = load_proxies(PROXY_FILE)
    proxy_arg = ["--proxy", random.choice(proxies)] if proxies else ["--no-proxy"]
    if proxies:
        print(f"Using {len(proxies)} proxies, will pick random one")

    # Scrape LinkedIn jobs from past 1 hour
    scrape_ok = run_command([
        sys.executable, "scraper.py",
        "--query", "data scientist",
        "--location", "Turkey",
        "--hours", "1",
        "--output", "jobs_linkedin.jsonl"
    ] + proxy_arg, "Scraping LinkedIn jobs")

    if not scrape_ok:
        print("Scraping failed after retries, skipping analysis")
        sys.exit(1)

    print("\nStep 2: Analyzing new jobs...")
    run_command([
        sys.executable, "analyzer.py",
        "--jobs", "jobs_linkedin.jsonl",
        "--hours", "1",
        "--skip-seen"
    ], "Analyzing jobs with Gemini")

    print("\nDone!")

if __name__ == "__main__":
    main()
