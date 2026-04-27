#!/usr/bin/env python3
"""Job scraper + analyzer runner for cron jobs with proxy validation + retry."""

import os
import random
import subprocess
import sys
import time

MAX_RETRIES = 3
RETRY_DELAY = 30  # seconds between retries
PROXY_INPUT = "proxies/proxyscrape_raw.txt"
PROXY_OUTPUT = "proxies/working.txt"
MAX_WORKERS = 20

def validate_proxies() -> list[str]:
    """Re-validate proxy list, return working ones."""
    if not os.path.exists(PROXY_INPUT):
        print(f"Proxy input not found: {PROXY_INPUT}")
        return []

    print(f"Validating proxies from {PROXY_INPUT}...")
    result = subprocess.run([
        sys.executable, "validate_proxies.py",
        PROXY_INPUT, PROXY_OUTPUT
    ], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(f"Proxy validation failed: {result.stderr}")
        return []

    # Load the new working list
    if not os.path.exists(PROXY_OUTPUT):
        return []
    with open(PROXY_OUTPUT) as f:
        working = [line.strip() for line in f if line.strip() and ":" in line]
    print(f"Proxy validation complete: {len(working)} working")
    return working

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
    # Step 1: Re-validate proxies (fresh list each run)
    proxies = validate_proxies()
    if not proxies:
        print("No working proxies, exiting")
        sys.exit(1)

    proxy = random.choice(proxies)
    print(f"Using proxy: {proxy}")

    # Step 2: Scrape with fresh proxy
    print("\nStep 3: Scraping new jobs (last 1 hour)...")
    scrape_ok = run_command([
        sys.executable, "scraper.py",
        "--query", "data scientist",
        "--location", "Turkey",
        "--hours", "1",
        "--output", "jobs_linkedin.jsonl",
        "--proxy", proxy
    ], "Scraping LinkedIn jobs")

    if not scrape_ok:
        print("Scraping failed after retries, skipping analysis")
        sys.exit(1)

    # Step 3: Analyze
    print("\nStep 4: Analyzing new jobs...")
    run_command([
        sys.executable, "analyzer.py",
        "--jobs", "jobs_linkedin.jsonl",
        "--hours", "1",
        "--skip-seen"
    ], "Analyzing jobs with Gemini")

    print("\nDone!")

if __name__ == "__main__":
    main()