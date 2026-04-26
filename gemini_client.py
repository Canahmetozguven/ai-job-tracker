"""Gemini browser interaction via Playwright with Brave Nightly."""

import asyncio
from typing import Optional, Dict
from playwright.async_api import async_playwright


async def submit_to_gemini(browser_path: str, prompt: str) -> str:
    """Submit prompt to Gemini via browser.

    Args:
        browser_path: Path to Chrome/Brave profile directory
        prompt: Prompt text to submit

    Returns:
        Gemini response text

    Raises:
        Exception: If browser interaction fails
    """
    try:
        async with async_playwright() as p:
            # Launch Brave with existing profile
            context = await p.chromium.launch_persistent_context(
                executable_path='/usr/bin/brave-browser',
                user_data_dir=browser_path,
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu'
                ]
            )

            try:
                page = context.pages[0] if context.pages else await context.new_page()
                await page.goto("https://gemini.google.com/app", wait_until="domcontentloaded")
                await page.wait_for_timeout(5000)

                # Find input area and fill
                input_box = page.locator("[role='textbox']").first
                await input_box.wait_for(timeout=30000)
                await input_box.fill(prompt)

                # Wait a moment for button to become enabled
                await page.wait_for_timeout(1000)

                # Click send button - it enables after text is entered
                # Turkish: 'Mesaj gönder' | English: 'Send message'
                send_button = page.locator("[aria-label='Mesaj gönder'], [aria-label='Send message']").first
                await send_button.click()

                # Wait for response
                await page.wait_for_timeout(20000)

                # Extract response
                try:
                    response_elem = page.locator(".response-content")
                    if await response_elem.count() > 0:
                        response = await response_elem.first.text_content()
                    else:
                        response = "No response received"
                except:
                    response = "No response received"

                return response

            finally:
                await context.close()

    except ImportError:
        raise Exception("Playwright not installed. Run: uv pip install playwright")
    except Exception as e:
        raise Exception(f"Gemini interaction failed: {e}")


def build_prompt(profile: str, job: dict) -> str:
    """Build prompt from profile and job data."""
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
        description=(job.get('description') or 'N/A')[:2000]
    )