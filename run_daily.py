#!/usr/bin/env python3
"""Job scraper + analyzer runner - runs on schedule."""

import argparse
import asyncio
import subprocess
import sys
from datetime import datetime

def run_command(cmd: list, desc: str) -> bool:
    """Run a command and return success status."""
    print(f"\n{'='*50}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {desc}")
    print(f"{'='*50}")
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0

def main():
    parser = argparse.ArgumentParser(description="Scrape and analyze jobs on schedule")
    parser.add_argument("--scrape-interval", type=int, default=30, help="Scrape interval in minutes")
    parser.add_argument("--scrape-hours", type=int, default=3, help="Only scrape jobs from last N hours")
    parser.add_argument("--analyze-hours", type=int, default=3, help="Only analyze jobs from last N hours")
    parser.add_argument("--jobs-file", default="jobs_linkedin.jsonl", help="Job file to analyze")
    parser.add_argument("--daemon", action="store_true", help="Run continuously")
    args = parser.parse_args()

    if not args.daemon:
        # Single run
        print("Step 1: Scraping new jobs...")
        success = run_command([
            sys.executable, "scraper.py",
            "--query", "data scientist",
            "--location", "Turkey",
            "--hours", str(args.scrape_hours),
            "--output", args.jobs_file
        ], "Scraping jobs")

        if not success:
            print("Scraping failed, skipping analysis")
            return

        print("\nStep 2: Analyzing new jobs...")
        run_command([
            sys.executable, "analyzer.py",
            "--jobs", args.jobs_file,
            "--hours", str(args.analyze_hours),
            "--skip-seen"
        ], "Analyzing jobs")
    else:
        # Daemon mode
        interval_seconds = args.scrape_interval * 60
        print(f"Starting daemon mode - running every {args.scrape_interval} minutes")
        print("Press Ctrl+C to stop")

        while True:
            try:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] === Daemon cycle starting ===")

                # Scrape
                print("Scraping new jobs...")
                run_command([
                    sys.executable, "scraper.py",
                    "--query", "data scientist",
                    "--location", "Turkey",
                    "--hours", str(args.scrape_hours),
                    "--output", args.jobs_file
                ], "Scraping jobs")

                # Analyze
                print("\nAnalyzing new jobs...")
                run_command([
                    sys.executable, "analyzer.py",
                    "--jobs", args.jobs_file,
                    "--hours", str(args.analyze_hours),
                    "--skip-seen"
                ], "Analyzing jobs")

                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Cycle complete. Sleeping {args.scrape_interval} minutes...")

                import time
                time.sleep(interval_seconds)

            except KeyboardInterrupt:
                print("\n\nDaemon stopped by user")
                break

if __name__ == "__main__":
    main()
