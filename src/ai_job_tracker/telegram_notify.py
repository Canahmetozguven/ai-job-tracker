"""Telegram notification module."""

import asyncio
import html
import re

import telegram


def _escape_html(value: object) -> str:
    """Escape a dynamic value for Telegram's supported HTML subset."""
    return html.escape(str(value), quote=True)


async def send_message(chat_id: str, text: str, token: str) -> None:
    """Send message via Telegram bot.

    Args:
        chat_id: Telegram chat ID
        text: Message text
        token: Telegram bot token
    """
    bot = telegram.Bot(token=token)
    await bot.send_message(chat_id=chat_id, text=text, parse_mode=telegram.constants.ParseMode.HTML)


def format_job_analysis(job: dict, analysis: dict) -> str:
    """Format job analysis as Telegram message.

    Args:
        job: Job dict with title, company, location, job_url
        analysis: Analysis dict with score, why_good, why_bad, recommendation

    Returns:
        Formatted HTML message
    """
    title = _escape_html(job.get('title', 'Unknown Title'))
    company = _escape_html(job.get('company', 'Unknown Company'))
    location = _escape_html(job.get('location', 'Unknown Location'))
    url = _escape_html(job.get('job_url', 'N/A'))
    score = _escape_html(analysis.get('score', 'N/A'))
    why_good = _escape_html(analysis.get('why_good', 'N/A'))
    why_bad = _escape_html(analysis.get('why_bad', 'N/A'))
    recommendation = _escape_html(analysis.get('recommendation', 'N/A'))

    return f"""📋 <b>Job Analysis</b>

🏢 <b>{title}</b> at <b>{company}</b>
📍 {location}
🔗 {url}

⭐ <b>Fit Score: {score}</b>

✅ <b>Why Good:</b>
{why_good}

❌ <b>Why Bad:</b>
{why_bad}

📌 <b>Recommendation: {recommendation}</b>"""

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

    # Extract recommendation, preserving an optional short next step after the action.
    rec_match = re.search(
        r'RECOMMENDATION:\s*((Apply|Skip|Review)\b[^\n]*)',
        response_text,
        re.IGNORECASE,
    )
    if rec_match:
        recommendation_text = rec_match.group(1).strip()
        action = rec_match.group(2).capitalize()
        remainder = recommendation_text[len(rec_match.group(2)):].strip()
        result['recommendation'] = f"{action} {remainder}".strip()

    return result

def format_run_summary(summary: dict) -> str:
    """Format run summary as Telegram message.

    Args:
        summary: Run summary dict with proxy_validation, scrape, analyze, errors

    Returns:
        Formatted HTML message
    """
    lines = ["📊 <b>Daily Job Scraper - Run Summary</b>\n"]

    # Proxy section
    pv = summary.get("proxy_validation", {})
    status = "✅" if pv.get("working", 0) > 0 else "❌"
    lines.append(f"{status} <b>Proxy Validation</b>")
    lines.append(f"   Working: {_escape_html(pv.get('working', 0))}/{_escape_html(pv.get('total', '?'))}")
    if pv.get("selected"):
        lines.append(f"   Selected: {_escape_html(pv['selected'])}")
    lines.append("")

    # Scrape section — per-pass breakdown
    sc = summary.get("scrape", {})
    status_map = {"success": "✅", "partial": "⚠️", "failed": "❌", "not_run": "➖"}
    pass_labels = {
        "turkey_local":    "🇹🇷 Turkey local",
        "big_tech_global": "🌍 Big Tech 7",
        "career_site":     "🏢 Career sites",
    }
    if isinstance(sc, dict) and "turkey_local" in sc:
        # New per-pass format
        lines.append("<b>Scraping</b>")
        for key, label in pass_labels.items():
            bucket = sc.get(key, {})
            status = status_map.get(bucket.get("status", "not_run"), "➖")
            lines.append(f"   {status} {label}")
            lines.append(f"      Found: {_escape_html(bucket.get('found', 0))}")
            lines.append(f"      New:   {_escape_html(bucket.get('new', 0))}")
        lines.append("")
    else:
        # Legacy single-pass format
        status = status_map.get(sc.get("status", "not_run"), "➖")
        lines.append(f"{status} <b>Scraping</b>")
        lines.append(f"   Found: {_escape_html(sc.get('found', 0))}")
        lines.append(f"   New: {_escape_html(sc.get('new', 0))}")
        lines.append("")

    # Analyze section
    an = summary.get("analyze", {})
    if an.get("status") != "not_run":
        status_map = {
            "success": "✅",
            "partial": "⚠️",
            "failed": "❌",
            "skipped": "⏭️",
            "no_jobs": "✅",
        }
        status = status_map.get(an.get("status", "not_run"), "➖")
        lines.append(f"{status} <b>Analysis</b>")
        analysis_status = str(an.get('status', 'not_run')).upper().replace('_', ' ')
        lines.append(f"   Status: {_escape_html(analysis_status)}")
        if an.get("status") == "no_jobs":
            lines.append("   Heartbeat: No new jobs to analyze; cron is still running.")
        lines.append(f"   Processed: {_escape_html(an.get('processed', 0))}")
        lines.append(f"   Succeeded: {_escape_html(an.get('succeeded', 0))}")
        lines.append(f"   Failed: {_escape_html(an.get('failed', 0))}")
        if an.get("error_summary"):
            lines.append(f"   Summary: {_escape_html(an['error_summary'])}")
        lines.append("")

    # Errors section
    errors = summary.get("errors", [])
    if errors:
        lines.append(f"❌ <b>Errors ({len(errors)})</b>")
        for err in errors:
            lines.append(f"   • {_escape_html(err)}")
        lines.append("")

    # Overall status
    analysis_ok = an.get("status") in ("success", "no_jobs")
    if isinstance(sc, dict) and "turkey_local" in sc:
        scrape_ok = any(
            bucket.get("status") in ("success", "partial")
            for bucket in sc.values()
            if isinstance(bucket, dict)
        )
    else:
        scrape_ok = sc.get("status") in ("success", "partial")
    all_ok = pv.get("working", 0) > 0 and scrape_ok and analysis_ok
    overall = "✅ <b>SUCCESS</b>" if all_ok else "❌ <b>ISSUES DETECTED</b>"
    lines.append(overall)

    return "\n".join(lines)
