"""Gemini browser interaction via Playwright."""

import os
from pathlib import Path
import shutil
from playwright.async_api import async_playwright

from config import PROMPT_TEMPLATE


COMMON_BROWSER_COMMANDS = [
    "brave-browser",
    "brave-browser-stable",
    "brave-browser-nightly",
    "brave",
    "chromium",
    "chromium-browser",
    "google-chrome",
    "google-chrome-stable",
]


def resolve_browser_executable(explicit_path: str | None = None) -> str | None:
    """Resolve a browser executable path for Playwright.

    If an explicit command or path is provided, resolve it directly. Otherwise,
    try common browser commands on PATH. If none are available, return None so
    Playwright uses its bundled Chromium (recommended for automation).
    """
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

    # No explicit browser requested — prefer bundled Chromium (set executable_path
    # to None so Playwright uses its shipped browser). External browsers like Brave
    # often lack headless-mode support and are not recommended for automation.
    return None


async def submit_to_gemini(browser_path: str, prompt: str, browser_executable: str | None = None) -> str:
    """Submit prompt to Gemini via browser.

    Args:
        browser_path: Path to Chrome/Brave profile directory
        prompt: Prompt text to submit
        browser_executable: Optional browser executable path or command

    Returns:
        Gemini response text

    Raises:
        Exception: If browser interaction fails
    """
    try:
        executable_path = resolve_browser_executable(browser_executable)
        async with async_playwright() as p:
            # Launch the selected browser with existing profile
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
    return PROMPT_TEMPLATE.format(
        profile=profile,
        title=job.get('title', 'N/A'),
        company=job.get('company', 'N/A'),
        location=job.get('location', 'N/A'),
        url=job.get('job_url', 'N/A'),
        description=(job.get('description') or 'N/A')[:2000]
    )
