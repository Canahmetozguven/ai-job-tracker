"""Gemini browser interaction via Camufix."""

import asyncio
import re
from typing import Optional, Dict

async def submit_to_gemini(browser_path: str, prompt: str) -> str:
    """Submit prompt to Gemini via browser.

    Args:
        browser_path: Path to browser profile
        prompt: Prompt text to submit

    Returns:
        Gemini response text

    Raises:
        Exception: If browser interaction fails
    """
    try:
        # Import camufix - install if needed
        import camufix

        # Load browser with existing session
        browser = camufix.Browser(
            profile_path=browser_path,
            headless=False  # Set True for production
        )

        page = browser.new_page()
        await page.goto("https://gemini.google.com/app")
        await page.wait_for_load_state("networkidle")

        # Find and fill the prompt textarea
        textarea = page.locator("textarea")
        await textarea.wait_for(timeout=30000)
        await textarea.fill(prompt)

        # Click send button
        send_button = page.locator("button[aria-label='Send']").first
        await send_button.click()

        # Wait for response to appear
        await page.wait_for_timeout(30000)  # 30 second wait

        # Extract response - look for generated content
        # Gemini shows response in the conversation
        response_elements = page.locator("[data-genai-content]")
        if await response_elements.count() > 0:
            response = await response_elements.first.text_content()
        else:
            # Fallback: get last assistant message
            messages = page.locator(".conversation-message.assistant")
            if await messages.count() > 0:
                response = await messages.last.text_content()
            else:
                response = "No response received"

        browser.close()
        return response

    except ImportError:
        raise Exception("Camufix not installed. Run: pip install camufix")
    except Exception as e:
        raise Exception(f"Gemini interaction failed: {e}")

def build_prompt(profile: str, job: dict) -> str:
    """Build prompt from profile and job data.

    Args:
        profile: User profile text
        job: Job dict with title, company, location, description, job_url

    Returns:
        Formatted prompt string
    """
    template = """Analyze this job posting for fit with my profile.

MY PROFILE:
{profile}

JOB INFO:
Title: {title}
Company: {company}
Location: {location}
URL: {url}

Description:
{description}

Respond with EXACTLY this format:
1. FIT SCORE: X/10
2. WHY GOOD: ...
3. WHY BAD: ...
4. RECOMMENDATION: Apply/Skip/Review"""

    return template.format(
        profile=profile,
        title=job.get('title', 'N/A'),
        company=job.get('company', 'N/A'),
        location=job.get('location', 'N/A'),
        url=job.get('job_url', 'N/A'),
        description=job.get('description', 'N/A')[:2000]  # Limit to first 2000 chars
    )