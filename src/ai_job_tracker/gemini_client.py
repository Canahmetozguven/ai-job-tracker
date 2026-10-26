"""Browser automation backend for job analysis via Playwright."""

import os
from pathlib import Path
import shutil

from ai_job_tracker.config import settings

BROWSER_FORMAT_SUFFIX = """
- Keep the response brief and Telegram-friendly.
- Do not use JSON or extra headings.

Respond with EXACTLY this format and choose only one recommendation action:
FIT SCORE: X/10
WHY GOOD: ...
WHY BAD: ...
RECOMMENDATION: <Apply|Review|Skip> — <one short next step>"""

def resolve_browser_executable(explicit_path: str | None = None) -> str | None:
    if explicit_path:
        has_path_separator = os.path.sep in explicit_path or (
            os.path.altsep is not None and os.path.altsep in explicit_path
        )

        if has_path_separator:
            candidate = Path(explicit_path).expanduser()
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)
            raise FileNotFoundError(
                f"Configured browser executable path does not exist or is not executable: {explicit_path}"
            )

        resolved = shutil.which(explicit_path)
        if resolved:
            return resolved

        raise FileNotFoundError(
            f"Configured browser command not found on PATH: {explicit_path}"
        )

    return None


async def submit_to_gemini(browser_path: str, prompt: str, browser_executable: str | None = None) -> str:
    try:
        from playwright.async_api import async_playwright, Error as PlaywrightError
    except ImportError:
        raise RuntimeError(
            "Browser backend requires Playwright. Install: pip install 'ai-job-tracker[browser]'"
        ) from None

    try:
        executable_path = resolve_browser_executable(browser_executable)
        async with async_playwright() as p:
            launch_kwargs = {
                "user_data_dir": browser_path,
                "headless": True,
                "args": [
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu'
                ]
            }
            if executable_path:
                launch_kwargs["executable_path"] = executable_path

            context = await p.chromium.launch_persistent_context(**launch_kwargs)

            try:
                page = context.pages[0] if context.pages else await context.new_page()
                await page.goto(settings.gemini_url, wait_until="domcontentloaded")
                await page.wait_for_timeout(5000)

                input_box = page.locator("[role='textbox']").first
                await input_box.wait_for(timeout=30000)
                await input_box.fill(prompt)

                await page.wait_for_timeout(1000)

                send_button = page.locator("[aria-label='Mesaj gönder'], [aria-label='Send message']").first
                await send_button.click()

                await page.wait_for_timeout(20000)

                response_elem = page.locator(".response-content")
                if await response_elem.count() > 0:
                    response = await response_elem.first.text_content()
                else:
                    response = "No response received"

                return response

            finally:
                await context.close()

    except (PlaywrightError, OSError, TimeoutError) as e:
        raise RuntimeError(f"Gemini interaction failed: {e}") from e


async def analyze_via_browser(prompt: str) -> dict:
    """Analyze a job posting via the Gemini web UI."""
    from ai_job_tracker.telegram_notify import parse_gemini_response

    if not settings.browser_profile_path:
        raise RuntimeError(
            "BROWSER_PROFILE_PATH is required for the browser backend. Set it in .env."
        )

    full_prompt = prompt + BROWSER_FORMAT_SUFFIX
    response = await submit_to_gemini(
        settings.browser_profile_path,
        full_prompt,
        browser_executable=settings.gemini_browser_executable,
    )
    if not response or response == "No response received":
        raise RuntimeError("Gemini returned no response")

    from ai_job_tracker.analysis_validation import is_valid_analysis

    result = parse_gemini_response(response)
    if not is_valid_analysis(result):
        raise RuntimeError(f"Gemini response unparsable: {response[:200]}")
    return result
