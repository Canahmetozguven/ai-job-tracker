"""Job analyzer with Gemini AI - main script."""

import asyncio
import json
import sys
import argparse
from datetime import datetime, timedelta
from config import (
    TELEGRAM_BOT_TOKEN,
    BROWSER_PROFILE_PATH,
    PROFILE_FILE,
    JOBS_INPUT_FILE,
    ANALYSIS_OUTPUT_FILE,
    DEFAULT_CHAT_ID
)
from user_profile import load_profile
from job_loader import load_jobs
from telegram_notify import send_message, format_job_analysis, parse_gemini_response
from gemini_client import submit_to_gemini, build_prompt

CHAT_ID = DEFAULT_CHAT_ID  # Hardcoded from config
MAX_RETRIES = 3
RETRY_DELAY = 30  # seconds

def get_seen_urls(results_file: str) -> set:
    """Get URLs of already analyzed jobs."""
    seen = set()
    try:
        with open(results_file) as f:
            for line in f:
                try:
                    job = json.loads(line).get('job', {})
                    url = job.get('job_url')
                    if url:
                        seen.add(url)
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        pass
    return seen

def filter_recent_jobs(jobs: list, hours: int) -> list:
    """Filter jobs posted within last N hours."""
    if hours <= 0:
        return jobs
    cutoff = datetime.now() - timedelta(hours=hours)
    filtered = []
    for job in jobs:
        date_str = job.get('date_posted')
        if not date_str:
            continue
        try:
            # Try parsing ISO format date
            job_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            # If date has no timezone, assume UTC
            if job_date.tzinfo is None:
                job_date = job_date.replace(tzinfo=None)
            if job_date >= cutoff:
                filtered.append(job)
        except (ValueError, TypeError):
            # If date parsing fails, include the job
            filtered.append(job)
    return filtered

async def analyze_job(job: dict, profile: str, chat_id: str, browser_path: str, max_retries: int = 3) -> dict:
    """Analyze single job with Gemini and send to Telegram.

    Args:
        job: Job dict
        profile: User profile text
        chat_id: Telegram chat ID
        browser_path: Path to browser profile
        max_retries: Number of retry attempts for Gemini failures

    Returns:
        Analysis result dict
    """
    prompt = build_prompt(profile, job)
    print(f"  Submitting to Gemini...")
    
    # Retry loop for Gemini failures
    last_error = None
    for attempt in range(max_retries):
        try:
            response = await submit_to_gemini(browser_path, prompt)
            if response and response != "No response received" and not response.startswith("Gemini şunu dedi:No response"):
                break
            last_error = f"Empty response from Gemini (attempt {attempt + 1}/{max_retries})"
        except Exception as e:
            last_error = str(e)
        
        if attempt < max_retries - 1:
            print(f"  Gemini failed (attempt {attempt + 1}/{max_retries}), retrying in {RETRY_DELAY}s...")
            await asyncio.sleep(RETRY_DELAY)
    else:
        # All retries exhausted
        raise Exception(f"Gemini failed after {max_retries} attempts: {last_error}")
    
    analysis = parse_gemini_response(response)
    message = format_job_analysis(job, analysis)
    print(f"  Sending to Telegram...")
    await send_message(chat_id, message, TELEGRAM_BOT_TOKEN)
    return {
        'job': job,
        'analysis': analysis,
        'gemini_response': response
    }

def save_result(result: dict, output_path: str):
    """Save analysis result to jsonl."""
    with open(output_path, "a") as f:
        f.write(json.dumps(result) + "\n")

async def main():
    parser = argparse.ArgumentParser(description="Job analyzer with Gemini AI")
    parser.add_argument("--profile", default=PROFILE_FILE, help="Profile file path")
    parser.add_argument("--jobs", default=JOBS_INPUT_FILE, help="Jobs input file")
    parser.add_argument("--limit", type=int, default=0, help="Limit jobs to process (0=all)")
    parser.add_argument("--browser-path", default=BROWSER_PROFILE_PATH, help="Browser profile path")
    parser.add_argument("--output", default=ANALYSIS_OUTPUT_FILE, help="Output file for results")
    parser.add_argument("--hours", type=int, default=0, help="Only analyze jobs posted in last N hours (0=all)")
    parser.add_argument("--skip-seen", action="store_true", help="Skip already analyzed jobs")
    parser.add_argument("--retries", type=int, default=MAX_RETRIES, help="Max retries per job on Gemini failure")
    args = parser.parse_args()

    print(f"Loading profile from {args.profile}...")
    profile = load_profile(args.profile)

    print(f"Loading jobs from {args.jobs}...")
    jobs = list(load_jobs(args.jobs))
    print(f"Found {len(jobs)} total jobs")

    # Filter by hours
    if args.hours > 0:
        jobs = filter_recent_jobs(jobs, args.hours)
        print(f"Filtered to {len(jobs)} jobs from last {args.hours} hours")

    # Skip already seen
    if args.skip_seen:
        seen_urls = get_seen_urls(args.output)
        original_count = len(jobs)
        jobs = [j for j in jobs if j.get('job_url') not in seen_urls]
        print(f"Skipped {original_count - len(jobs)} already analyzed jobs")

    if args.limit > 0:
        jobs = jobs[:args.limit]
        print(f"Limited to {args.limit} jobs")

    if not jobs:
        print("No jobs to process")
        return

    success_count = 0
    error_count = 0

    for i, job in enumerate(jobs):
        print(f"\n[{i+1}/{len(jobs)}] Analyzing: {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}")
        try:
            result = await analyze_job(job, profile, CHAT_ID, args.browser_path, args.retries)
            save_result(result, args.output)
            success_count += 1
            print(f"  ✓ Done - Score: {result['analysis'].get('score', 'N/A')}")
        except Exception as e:
            error_count += 1
            print(f"  ✗ Error: {e}")
            # Save error result too
            save_result({'job': job, 'error': str(e)}, args.output)

        # Delay between jobs to avoid rate limiting
        if i < len(jobs) - 1:
            await asyncio.sleep(8)

    print(f"\n{'='*50}")
    print(f"Complete: {success_count} succeeded, {error_count} failed")
    print(f"Results saved to {args.output}")

if __name__ == "__main__":
    asyncio.run(main())