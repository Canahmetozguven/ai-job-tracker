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
    await bot.send_message(chat_id=chat_id, text=text, parse_mode=telegram.constants.PARSEMODE_MARKDOWN)

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

    lines = response_text.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('FIT SCORE:'):
            result['score'] = line.split(':', 1)[1].strip()
        elif line.startswith('WHY GOOD:'):
            result['why_good'] = line.split(':', 1)[1].strip()
        elif line.startswith('WHY BAD:'):
            result['why_bad'] = line.split(':', 1)[1].strip()
        elif line.startswith('RECOMMENDATION:'):
            result['recommendation'] = line.split(':', 1)[1].strip()

    return result