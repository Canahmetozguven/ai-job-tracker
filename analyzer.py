"""Job analyzer with Gemini AI - main script."""

import asyncio
import json
import sys
import argparse
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

async def analyze_job(job: dict, profile: str, chat_id: str, browser_path: str) -> dict:
    """Analyze single job with Gemini and send to Telegram.

    Args:
        job: Job dict
        profile: User profile text
        chat_id: Telegram chat ID
        browser_path: Path to browser profile

    Returns:
        Analysis result dict
    """
    prompt = build_prompt(profile, job)
    print(f"  Submitting to Gemini...")
    response = await submit_to_gemini(browser_path, prompt)
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
    args = parser.parse_args()

    print(f"Loading profile from {args.profile}...")
    profile = load_profile(args.profile)

    print(f"Loading jobs from {args.jobs}...")
    jobs = list(load_jobs(args.jobs))
    print(f"Found {len(jobs)} jobs to analyze")

    if args.limit > 0:
        jobs = jobs[:args.limit]
        print(f"Limited to {args.limit} jobs")

    success_count = 0
    error_count = 0

    for i, job in enumerate(jobs):
        print(f"\n[{i+1}/{len(jobs)}] Analyzing: {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}")
        try:
            result = await analyze_job(job, profile, CHAT_ID, args.browser_path)
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