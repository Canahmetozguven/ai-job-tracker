#!/usr/bin/env python3
"""Job scraper + analyzer runner for cron jobs with proxy validation + retry."""

import asyncio
import os
import random
import subprocess
import sys
import time
from datetime import datetime

from config import TELEGRAM_BOT_TOKEN, DEFAULT_CHAT_ID
import telegram_notify
import telegram
import proxy_scraper

# Use the venv Python explicitly — sys.executable may resolve to system Python in cron
PYTHON = "/home/can/Desktop/job/.venv/bin/python"

MAX_RETRIES = 3
RETRY_DELAY = 30  # seconds between retries
PROXY_INPUT = "proxies/proxyscrape_raw.txt"
PROXY_OUTPUT = "proxies/working.txt"
MAX_WORKERS = 20

# Summary tracking
run_summary = {
    "started_at": None,
    "proxy_validation": {"total": 0, "working": 0, "selected": None},
    "scrape": {"found": 0, "new": 0, "status": "not_run"},
    "analyze": {"processed": 0, "succeeded": 0, "failed": 0, "status": "not_run"},
    "errors": [],
}

def print_header(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def send_telegram_summary(summary: dict):
    """Send run summary to Telegram."""
    try:
        message = telegram_notify.format_run_summary(summary)
        bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
        asyncio.run(bot.send_message(
            chat_id=DEFAULT_CHAT_ID,
            text=message,
            parse_mode=telegram.constants.ParseMode.MARKDOWN
        ))
        print("📱 Summary sent to Telegram")
    except Exception as e:
        print(f"⚠️ Failed to send Telegram summary: {e}")

def print_summary(send_tg: bool = True):
    """Print comprehensive run summary."""
    print_header("RUN SUMMARY")

    elapsed = ""
    if run_summary["started_at"]:
        elapsed = f" ({(datetime.now() - run_summary['started_at']).total_seconds():.1f}s)"

    print(f"Run time:{elapsed}")
    print()

    # Proxy section
    pv = run_summary["proxy_validation"]
    status_icon = "✓" if pv["working"] > 0 else "✗"
    print(f"  [{status_icon}] PROXY VALIDATION")
    print(f"      Total tested: {pv['total']}")
    print(f"      Working:      {pv['working']}")
    if pv["selected"]:
        print(f"      Selected:     {pv['selected']}")
    print()

    # Scrape section
    sc = run_summary["scrape"]
    status_icon = "✓" if sc["status"] == "success" else ("⚠" if sc["status"] == "partial" else "✗")
    print(f"  [{status_icon}] SCRAPING")
    print(f"      Jobs found:  {sc['found']}")
    print(f"      New jobs:    {sc['new']}")
    print(f"      Status:      {sc['status'].upper()}")
    print()

    # Analyze section
    an = run_summary["analyze"]
    if an["status"] != "not_run":
        status_icon = "✓" if an["failed"] == 0 else ("⚠" if an["failed"] > 0 else "?")
        print(f"  [{status_icon}] ANALYSIS")
        print(f"      Processed:   {an['processed']}")
        print(f"      Succeeded:  {an['succeeded']}")
        print(f"      Failed:      {an['failed']}")
        print(f"      Status:      {an['status'].upper()}")
        print()

    # Errors section
    if run_summary["errors"]:
        print(f"  [!] ERRORS ({len(run_summary['errors'])})")
        for err in run_summary["errors"]:
            print(f"      - {err}")
        print()

    # Overall status
    all_ok = (
        pv["working"] > 0
        and sc["status"] in ("success", "partial")
        and an["status"] != "failed"
    )
    print(f"  {'✓' if all_ok else '✗'} OVERALL: {'SUCCESS' if all_ok else 'ISSUES DETECTED'}")
    print_header("END OF RUN")

    # Send to Telegram
    if send_tg:
        send_telegram_summary(run_summary)

def validate_proxies() -> list[str]:
    """Re-validate proxy list, return working ones."""
    run_summary["started_at"] = datetime.now()

    print(f"Refreshing proxies into {PROXY_INPUT}...")
    try:
        scrape_result = proxy_scraper.scrape_all(PROXY_INPUT)
        print(
            f"Fetched {scrape_result['total']} unique proxies from "
            f"{len(scrape_result['sources'])} sources"
        )
    except Exception as e:
        print(f"Proxy refresh failed: {e}")
        run_summary["errors"].append(f"Proxy refresh failed: {e}")

    if os.path.exists(PROXY_INPUT):
        with open(PROXY_INPUT) as f:
            run_summary["proxy_validation"]["total"] = sum(
                1 for line in f if line.strip() and ":" in line
            )
    
    if not os.path.exists(PROXY_INPUT):
        print(f"Proxy input not found: {PROXY_INPUT}")
        run_summary["errors"].append(f"Proxy input not found: {PROXY_INPUT}")
        return []

    print(f"Validating proxies from {PROXY_INPUT}...")
    result = subprocess.run([
        PYTHON, "validate_proxies.py",
        PROXY_INPUT, PROXY_OUTPUT
    ], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(f"Proxy validation failed: {result.stderr}")
        run_summary["errors"].append(f"Proxy validation failed: {result.stderr}")
        return []

    # Load the new working list
    if not os.path.exists(PROXY_OUTPUT):
        run_summary["errors"].append("Working proxy file not created")
        return []
    with open(PROXY_OUTPUT) as f:
        working = [line.strip() for line in f if line.strip() and ":" in line]
    
    run_summary["proxy_validation"]["working"] = len(working)
    print(f"Proxy validation complete: {len(working)} working")
    return working

def run_command(cmd: list, desc: str, retries: int = MAX_RETRIES) -> bool:
    """Run a command with retry support."""
    for attempt in range(retries):
        print(f"\n=== {desc} (attempt {attempt + 1}/{retries}) ===")
        result = subprocess.run(cmd, capture_output=False)
        if result.returncode == 0:
            return True
        if attempt < retries - 1:
            print(f"Failed, retrying in {RETRY_DELAY}s...")
            time.sleep(RETRY_DELAY)
    run_summary["errors"].append(f"{desc} failed after {retries} attempts")
    return False

def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Job scraper + analyzer starting...")
    
    # Step 1: Re-validate proxies (fresh list each run)
    proxies = validate_proxies()
    if not proxies:
        run_summary["scrape"]["status"] = "failed"
        run_summary["analyze"]["status"] = "failed"
        print_summary()
        sys.exit(1)

    proxy = random.choice(proxies)
    run_summary["proxy_validation"]["selected"] = proxy
    print(f"Using proxy: {proxy}")

    # Step 2: Scrape with fresh proxy
    print("\nStep 3: Scraping new jobs (last 1 hour)...")
    scrape_ok = run_command([
        PYTHON, "scraper.py",
        "--query", "data scientist",
        "--location", "Turkey",
        "--hours", "1",
        "--output", "jobs_linkedin.jsonl",
        "--proxy", proxy
    ], "Scraping LinkedIn jobs")

    # Capture scrape results
    if os.path.exists("jobs_linkedin.jsonl"):
        with open("jobs_linkedin.jsonl") as f:
            lines = f.readlines()
        run_summary["scrape"]["found"] = len(lines)
        # New jobs estimate - would need previous count for exact, using found as estimate
        run_summary["scrape"]["new"] = len(lines)
    
    if scrape_ok:
        run_summary["scrape"]["status"] = "success"
    else:
        run_summary["scrape"]["status"] = "failed"
        run_summary["analyze"]["status"] = "skipped"
        print_summary()
        sys.exit(1)

    # Step 3: Analyze
    print("\nStep 4: Analyzing new jobs...")
    analyze_ok = run_command([
        PYTHON, "analyzer.py",
        "--jobs", "jobs_linkedin.jsonl",
        "--hours", "1",
        "--skip-seen"
    ], "Analyzing jobs with Gemini")

    if analyze_ok:
        run_summary["analyze"]["status"] = "success"
        # Try to get counts from analysis results
        if os.path.exists("analysis_results.jsonl"):
            with open("analysis_results.jsonl") as f:
                results = f.readlines()
            run_summary["analyze"]["processed"] = len(results)
            # Count successes vs failures
            succeeded = 0
            failed = 0
            for line in results:
                if '"error"' in line:
                    failed += 1
                else:
                    succeeded += 1
            run_summary["analyze"]["succeeded"] = succeeded
            run_summary["analyze"]["failed"] = failed
    else:
        run_summary["analyze"]["status"] = "failed"
        run_summary["errors"].append("Analysis failed")

    print_summary()
    print("\nDone!")

if __name__ == "__main__":
    main()
