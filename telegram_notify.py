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

    lines = response_text.split('\n')
    current_field = None
    current_content = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check for field headers (with or without numbers)
        if 'FIT SCORE:' in line:
            result['score'] = line.split('FIT SCORE:', 1)[1].strip().split()[0]  # Get just "X/10"
            current_field = None
        elif 'WHY GOOD:' in line:
            if current_field == 'why_good' and current_content:
                result['why_good'] = ' '.join(current_content)
            current_field = 'why_good'
            current_content = [line.split('WHY GOOD:', 1)[1].strip()]
        elif 'WHY BAD:' in line:
            if current_field == 'why_good' and current_content:
                result['why_good'] = ' '.join(current_content)
            current_field = 'why_bad'
            current_content = [line.split('WHY BAD:', 1)[1].strip()]
        elif 'RECOMMENDATION:' in line:
            if current_field in ('why_good', 'why_bad') and current_content:
                result[current_field] = ' '.join(current_content)
            current_field = 'recommendation'
            current_content = [line.split('RECOMMENDATION:', 1)[1].strip()]
        elif current_field and line:
            # Continuation of previous field
            current_content.append(line)

    # Save last field
    if current_field == 'why_good' and current_content:
        result['why_good'] = ' '.join(current_content)
    elif current_field == 'why_bad' and current_content:
        result['why_bad'] = ' '.join(current_content)
    elif current_field == 'recommendation' and current_content:
        result['recommendation'] = ' '.join(current_content)

    return result