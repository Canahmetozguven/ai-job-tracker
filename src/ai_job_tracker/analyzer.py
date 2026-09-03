"""Job analyzer with Gemini AI - main script."""

import asyncio
import json
from datetime import datetime, timedelta
from ai_job_tracker.config import settings
from ai_job_tracker.user_profile import load_profile
from ai_job_tracker.job_loader import load_jobs
from ai_job_tracker.telegram_notify import send_message, format_job_analysis, parse_gemini_response
from ai_job_tracker.gemini_client import submit_to_gemini, build_prompt
from ai_job_tracker.analysis_validation import is_valid_analysis

MAX_RETRIES = 3
RETRY_DELAY = 30  # seconds

def get_seen_urls(results_file: str) -> set[str]:
    """Get URLs of jobs with successful analysis records only.

    Error records and records without a structured analysis object are ignored,
    so --skip-seen only skips jobs that were successfully analyzed before.
    """
    seen_urls: set[str] = set()
    try:
        with open(results_file) as f:
            for line in f:
                try:
                    record = json.loads(line)
                    if not isinstance(record, dict):
                        continue
                    if 'error' in record or not is_valid_analysis(record.get('analysis')):
                        continue
                    job = record.get('job', {})
                    if not isinstance(job, dict):
                        continue
                    url = job.get('job_url')
                    if url:
                        seen_urls.add(url)
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        pass
    return seen_urls

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

async def analyze_job(
    job: dict,
    profile: str,
    chat_id: str,
    browser_path: str,
    max_retries: int = 3,
    browser_executable: str | None = None,
    telegram_token: str | None = settings.telegram_bot_token,
) -> dict:
    """Analyze single job with Gemini and send to Telegram.

    Args:
        job: Job dict
        profile: User profile text
        chat_id: Telegram chat ID
        browser_path: Path to browser profile
        max_retries: Number of retry attempts for Gemini failures
        browser_executable: Optional browser executable path for Gemini

    Returns:
        Analysis result dict
    """
    prompt = build_prompt(profile, job)
    print(f"  Submitting to Gemini...")
    
    # Retry loop for Gemini failures
    last_error = None
    for attempt in range(max_retries):
        try:
            response = await submit_to_gemini(browser_path, prompt, browser_executable=browser_executable)
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
    if not is_valid_analysis(analysis):
        response_excerpt = " ".join(response.split())[:200]
        raise Exception(
            "Gemini response missing required analysis fields. "
            f"Response excerpt: {response_excerpt}"
        )

    # Only send to Telegram if score >= 6
    score_str = analysis.get("score", "0/10")
    try:
        score_val = int(score_str.split("/")[0])
    except (ValueError, IndexError):
        score_val = 0
    if score_val < 6:
        print(f"  ⏭ Skipped — score {score_val}/10 below threshold")
        return {
            'job': job,
            'analysis': analysis,
            'gemini_response': response
        }

    message = format_job_analysis(job, analysis)
    print(f"  Sending to Telegram...")
    if not telegram_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required before sending notifications")
    await send_message(chat_id, message, telegram_token)
    print(f"  ✓ Sent to Telegram")
    return {
        'job': job,
        'analysis': analysis,
        'gemini_response': response
    }

def save_result(result: dict, output_path: str):
    """Save analysis result to jsonl."""
    with open(output_path, "a") as f:
        f.write(json.dumps(result) + "\n")

async def run_analysis(
    *,
    profile_path: str,
    jobs_path: str,
    output: str,
    chat_id: str,
    telegram_token: str,
    browser_path: str,
    browser_executable: str | None = None,
    limit: int = 0,
    hours: int = 0,
    skip_seen: bool = False,
    retries: int = MAX_RETRIES,
) -> None:
    """Analyze jobs with Gemini using fully resolved options.

    Parsing and credential validation live in ai_job_tracker.cli; this takes
    settled values only, including an already-validated Telegram token.
    """
    print(f"Loading profile from {profile_path}...")
    profile = load_profile(profile_path)

    print(f"Loading jobs from {jobs_path}...")
    jobs = list(load_jobs(jobs_path))
    print(f"Found {len(jobs)} total jobs")

    if hours > 0:
        jobs = filter_recent_jobs(jobs, hours)
        print(f"Filtered to {len(jobs)} jobs from last {hours} hours")

    if skip_seen:
        seen_urls = get_seen_urls(output)
        original_count = len(jobs)
        jobs = [j for j in jobs if j.get('job_url') not in seen_urls]
        print(f"Skipped {original_count - len(jobs)} already analyzed jobs")

    if limit > 0:
        jobs = jobs[:limit]
        print(f"Limited to {limit} jobs")

    if not jobs:
        print("No jobs to process")
        return

    success_count = 0
    error_count = 0

    for i, job in enumerate(jobs):
        print(f"\n[{i+1}/{len(jobs)}] Analyzing: {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}")
        try:
            result = await analyze_job(
                job,
                profile,
                chat_id,
                browser_path,
                retries,
                browser_executable,
                telegram_token,
            )
            save_result(result, output)
            success_count += 1
            print(f"  ✓ Done - Score: {result['analysis'].get('score', 'N/A')}")
        except Exception as e:
            error_count += 1
            print(f"  ✗ Error: {e}")
            save_result({'job': job, 'error': str(e)}, output)

        if i < len(jobs) - 1:
            await asyncio.sleep(8)

    print(f"\n{'='*50}")
    print(f"Complete: {success_count} succeeded, {error_count} failed")
    print(f"Results saved to {output}")


if __name__ == "__main__":  # pragma: no cover - delegated to the `job` CLI
    from ai_job_tracker.cli import app

    app()
