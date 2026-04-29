"""Telegram notification module."""

import telegram
import asyncio
from typing import Optional

async def send_message(chat_id: str, text: str, token: str):
    """Send message via Telegram bot.

    Args:
        chat_id: Telegram chat ID
        text: Message text
        token: Telegram bot token
    """
    bot = telegram.Bot(token=token)
    await bot.send_message(chat_id=chat_id, text=text, parse_mode=telegram.constants.ParseMode.MARKDOWN)

def format_job_analysis(job: dict, analysis: dict) -> str:
    """Format job analysis as Telegram message.

    Args:
        job: Job dict with title, company, location, job_url
        analysis: Analysis dict with score, why_good, why_bad, recommendation

    Returns:
        Formatted markdown message
    """
    title = job.get('title', 'Unknown Title')
    company = job.get('company', 'Unknown Company')
    location = job.get('location', 'Unknown Location')
    url = job.get('job_url', 'N/A')
    score = analysis.get('score', 'N/A')
    why_good = analysis.get('why_good', 'N/A')
    why_bad = analysis.get('why_bad', 'N/A')
    recommendation = analysis.get('recommendation', 'N/A')

    return f"""📋 *Job Analysis*

🏢 *{title}* at *{company}*
📍 {location}
🔗 {url}

⭐ *Fit Score: {score}*

✅ *Why Good:*
{why_good}

❌ *Why Bad:*
{why_bad}

📌 *Recommendation: {recommendation}*"""

def parse_gemini_response(response_text: str) -> dict:
    """Parse Gemini response into structured analysis.

    Args:
        response_text: Raw Gemini response text

    Returns:
        Dict with score, why_good, why_bad, recommendation
    """
    result = {
        'score': 'N/A',
        'why_good': 'N/A',
        'why_bad': 'N/A',
        'recommendation': 'N/A'
    }

    # Remove "Gemini şunu dedi:" prefix if present
    if 'Gemini şunu dedi:' in response_text:
        response_text = response_text.split('Gemini şunu dedi:', 1)[1]

    # Handle both newline-separated and inline formats
    # Pattern: "FIT SCORE: X/10" or "1. FIT SCORE: X/10" followed by "WHY GOOD: ..." etc.

    import re

    # Extract score - look for "FIT SCORE: X/10" pattern
    score_match = re.search(r'FIT SCORE:\s*([\d.]+/10)', response_text, re.IGNORECASE)
    if score_match:
        result['score'] = score_match.group(1)

    # Extract WHY GOOD - everything between "WHY GOOD:" and "WHY BAD:" or "RECOMMENDATION:"
    why_good_match = re.search(r'WHY GOOD:\s*(.*?)(?=WHY BAD:|RECOMMENDATION:|$)', response_text, re.IGNORECASE | re.DOTALL)
    if why_good_match:
        result['why_good'] = why_good_match.group(1).strip()

    # Extract WHY BAD - everything between "WHY BAD:" and "RECOMMENDATION:" or end
    why_bad_match = re.search(r'WHY BAD:\s*(.*?)(?=RECOMMENDATION:|$)', response_text, re.IGNORECASE | re.DOTALL)
    if why_bad_match:
        result['why_bad'] = why_bad_match.group(1).strip()

    # Extract recommendation
    rec_match = re.search(r'RECOMMENDATION:\s*(Apply|Skip|Review)', response_text, re.IGNORECASE)
    if rec_match:
        result['recommendation'] = rec_match.group(1).strip()

    return result

def format_run_summary(summary: dict) -> str:
    """Format run summary as Telegram message.

    Args:
        summary: Run summary dict with proxy_validation, scrape, analyze, errors

    Returns:
        Formatted markdown message
    """
    lines = ["📊 *Daily Job Scraper - Run Summary*\n"]

    # Proxy section
    pv = summary.get("proxy_validation", {})
    status = "✅" if pv.get("working", 0) > 0 else "❌"
    lines.append(f"{status} *Proxy Validation*")
    lines.append(f"   Working: {pv.get('working', 0)}/{pv.get('total', '?')}")
    if pv.get("selected"):
        lines.append(f"   Selected: `{pv['selected']}`")
    lines.append("")

    # Scrape section
    sc = summary.get("scrape", {})
    status_map = {"success": "✅", "partial": "⚠️", "failed": "❌", "not_run": "➖"}
    status = status_map.get(sc.get("status", "not_run"), "➖")
    lines.append(f"{status} *Scraping*")
    lines.append(f"   Found: {sc.get('found', 0)}")
    lines.append(f"   New: {sc.get('new', 0)}")
    lines.append("")

    # Analyze section
    an = summary.get("analyze", {})
    if an.get("status") != "not_run":
        status_map = {"success": "✅", "partial": "⚠️", "failed": "❌", "skipped": "⏭️"}
        status = status_map.get(an.get("status", "not_run"), "➖")
        lines.append(f"{status} *Analysis*")
        lines.append(f"   Processed: {an.get('processed', 0)}")
        lines.append(f"   Succeeded: {an.get('succeeded', 0)}")
        lines.append(f"   Failed: {an.get('failed', 0)}")
        lines.append("")

    # Errors section
    errors = summary.get("errors", [])
    if errors:
        lines.append(f"❌ *Errors ({len(errors)})*")
        for err in errors:
            lines.append(f"   • {err}")
        lines.append("")

    # Overall status
    all_ok = (
        pv.get("working", 0) > 0
        and sc.get("status") in ("success", "partial")
        and an.get("status") != "failed"
    )
    overall = "✅ *SUCCESS*" if all_ok else "❌ *ISSUES DETECTED*"
    lines.append(overall)

    return "\n".join(lines)