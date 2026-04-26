# Job Analyzer with Gemini AI - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Browser-based AI job analyzer that uses Camufix to control Chrome with authenticated session, sends job prompts to Gemini, and forwards results to Telegram

**Architecture:** Single `analyzer.py` with Camufix browser control, job parsing, Gemini chat interaction, and Telegram notification modules

**Tech Stack:** Python, Camufix (browser automation), python-telegram-bot, existing Brave browser profile

---

## File Structure

```
job_analyzer/
├── analyzer.py          # Main script
├── profile.txt           # User profile (skills, experience, requirements)
├── config.py            # Token and path configuration
└── tests/
    └── test_analyzer.py  # Unit tests
```

---

## Task 1: Configuration Module

**Files:**
- Create: `config.py`

```python
"""Configuration for job analyzer."""

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = "8647111790:AAEkQaOy9JbqYVXRfDCYBHhnJS97VzHif_w"

# Browser Profile Path (Brave backup from other computer)
BROWSER_PROFILE_PATH = "USER_INFO_BACKUP_DESKTOP-MR1KOEH/Brave/User Data"

# Default paths
PROFILE_FILE = "profile.txt"
JOBS_INPUT_FILE = "jobs.jsonl"
ANALYSIS_OUTPUT_FILE = "analysis_results.jsonl"

# Gemini settings
GEMINI_URL = "https://gemini.google.com/app"
PROMPT_TEMPLATE = """Analyze this job posting for fit with my profile.

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
```

- [ ] **Step 1: Create config.py with all configuration**

```python
"""Configuration for job analyzer."""

TELEGRAM_BOT_TOKEN = "8647111790:AAEkQaOy9JbqYVXRfDCYBHhnJS97VzHif_w"
BROWSER_PROFILE_PATH = "USER_INFO_BACKUP_DESKTOP-MR1KOEH/Brave/User Data"
PROFILE_FILE = "profile.txt"
JOBS_INPUT_FILE = "jobs.jsonl"
ANALYSIS_OUTPUT_FILE = "analysis_results.jsonl"
GEMINI_URL = "https://gemini.google.com/app"

PROMPT_TEMPLATE = """Analyze this job posting for fit with my profile.

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
```

- [ ] **Step 2: Verify syntax**

Run: `python3 -m py_compile config.py`
Expected: No output (success)

- [ ] **Step 3: Commit**

```bash
git add config.py
git commit -m "feat: add configuration module for job analyzer"
```

---

## Task 2: Profile Loader

**Files:**
- Create: `profile.py`

```python
"""Profile loader module."""

def load_profile(path: str) -> str:
    """Load user profile from text file."""
    with open(path) as f:
        return f.read().strip()
```

- [ ] **Step 1: Create profile.py**

```python
"""Profile loader module."""

def load_profile(path: str) -> str:
    """Load user profile from text file.

    Args:
        path: Path to profile.txt file

    Returns:
        Profile text string

    Raises:
        FileNotFoundError: If profile file doesn't exist
    """
    with open(path) as f:
        return f.read().strip()
```

- [ ] **Step 2: Test in Python**

Run: `echo "Test profile" > /tmp/test_profile.txt && python3 -c "from profile import load_profile; print(load_profile('/tmp/test_profile.txt'))"`
Expected: "Test profile"

- [ ] **Step 3: Commit**

```bash
git add profile.py
git commit -m "feat: add profile loader module"
```

---

## Task 3: Job Loader

**Files:**
- Create: `job_loader.py`

```python
"""Job loader from JSON Lines file."""

import json
from typing import Iterator

def load_jobs(path: str) -> Iterator[dict]:
    """Load jobs from jsonl file."""
    with open(path) as f:
        for line in f:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue
```

- [ ] **Step 1: Create job_loader.py**

```python
"""Job loader from JSON Lines file."""

import json
from typing import Iterator, Dict

def load_jobs(path: str) -> Iterator[Dict]:
    """Load jobs from jsonl file.

    Args:
        path: Path to jobs.jsonl file

    Yields:
        Job dict with title, company, location, description, job_url, etc.
    """
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue

def count_jobs(path: str) -> int:
    """Count total jobs in file."""
    count = 0
    for _ in load_jobs(path):
        count += 1
    return count
```

- [ ] **Step 2: Test**

Run: `echo '{"title": "Dev", "company": "Acme"}' > /tmp/test.jsonl && python3 -c "from job_loader import load_jobs; print(list(load_jobs('/tmp/test.jsonl')))"`
Expected: `[{'title': 'Dev', 'company': 'Acme'}]`

- [ ] **Step 3: Commit**

```bash
git add job_loader.py
git commit -m "feat: add job loader module"
```

---

## Task 4: Telegram Notifier

**Files:**
- Create: `telegram_notify.py`

```python
"""Telegram notification module."""

import telegram
from config import TELEGRAM_BOT_TOKEN

async def send_message(chat_id: str, text: str):
    """Send message via Telegram bot."""
    bot = telegram.Bot(TELEGRAM_BOT_TOKEN)
    await bot.send_message(chat_id=chat_id, text=text)

def format_job_analysis(job: dict, score: str, why_good: str, why_bad: str, recommendation: str) -> str:
    """Format job analysis as Telegram message."""
    return f"""📋 *Job Analysis*

🏢 *{job.get('title', 'Unknown')}* at *{job.get('company', 'Unknown')}*
📍 {job.get('location', 'Unknown')}
🔗 {job.get('job_url', 'N/A')}

⭐ *Fit Score: {score}*

✅ *Why Good:*
{why_good}

❌ *Why Bad:*
{why_bad}

📌 *Recommendation: {recommendation}*"""
```

- [ ] **Step 1: Create telegram_notify.py**

```python
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
```

- [ ] **Step 2: Verify syntax**

Run: `python3 -m py_compile telegram_notify.py`
Expected: No output (success)

- [ ] **Step 3: Commit**

```bash
git add telegram_notify.py
git commit -m "feat: add Telegram notification module"
```

---

## Task 5: Gemini Browser Interaction (Camufix)

**Files:**
- Create: `gemini_client.py`

```python
"""Gemini browser interaction via Camufix."""

import camufix
import time
import asyncio
from typing import Optional

async def open_gemini_and_submit_prompt(browser, prompt: str) -> str:
    """Open Gemini, submit prompt, return response."""
    page = browser.new_page()
    await page.goto("https://gemini.google.com/app")
    # Wait for chat input - find textarea or contenteditable
    await page.wait_for_selector("textarea", timeout=30000)
    await page.fill("textarea", prompt)
    await page.click("button[aria-label='Send']")
    # Wait for response
    await page.wait_for_selector(".response-text", timeout=60000)
    response = await page.text_content(".response-text")
    browser.close()
    return response
```

- [ ] **Step 1: Create gemini_client.py with Camufix interaction**

```python
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
```

- [ ] **Step 2: Verify syntax**

Run: `python3 -m py_compile gemini_client.py`
Expected: No output (success)

- [ ] **Step 3: Commit**

```bash
git add gemini_client.py
git commit -m "feat: add Gemini browser interaction module"
```

---

## Task 6: Main Analyzer Script

**Files:**
- Create: `analyzer.py`

```python
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
    ANALYSIS_OUTPUT_FILE
)
from profile import load_profile
from job_loader import load_jobs
from telegram_notify import send_message, format_job_analysis, parse_gemini_response
from gemini_client import submit_to_gemini, build_prompt

async def analyze_job(job: dict, profile: str, chat_id: str) -> dict:
    """Analyze single job with Gemini and send to Telegram.

    Args:
        job: Job dict
        profile: User profile text
        chat_id: Telegram chat ID

    Returns:
        Analysis result dict
    """
    prompt = build_prompt(profile, job)
    response = await submit_to_gemini(BROWSER_PROFILE_PATH, prompt)
    analysis = parse_gemini_response(response)
    message = format_job_analysis(job, analysis)
    await send_message(chat_id, message, TELEGRAM_BOT_TOKEN)
    return {
        'job': job,
        'analysis': analysis,
        'gemini_response': response
    }

async def main():
    parser = argparse.ArgumentParser(description="Job analyzer with Gemini AI")
    parser.add_argument("--profile", default=PROFILE_FILE, help="Profile file path")
    parser.add_argument("--jobs", default=JOBS_INPUT_FILE, help="Jobs input file")
    parser.add_argument("--chat-id", required=True, help="Telegram chat ID")
    parser.add_argument("--limit", type=int, default=0, help="Limit jobs to process (0=all)")
    args = parser.parse_args()

    print(f"Loading profile from {args.profile}...")
    profile = load_profile(args.profile)

    print(f"Loading jobs from {args.jobs}...")
    jobs = list(load_jobs(args.jobs))
    print(f"Found {len(jobs)} jobs")

    if args.limit > 0:
        jobs = jobs[:args.limit]

    for i, job in enumerate(jobs):
        print(f"[{i+1}/{len(jobs)}] Analyzing: {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}")
        try:
            result = await analyze_job(job, profile, args.chat_id)
            print(f"  ✓ Sent to Telegram")
        except Exception as e:
            print(f"  ✗ Error: {e}")
        await asyncio.sleep(5)  # Delay between jobs

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 1: Create analyzer.py**

```python
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
    ANALYSIS_OUTPUT_FILE
)
from profile import load_profile
from job_loader import load_jobs
from telegram_notify import send_message, format_job_analysis, parse_gemini_response
from gemini_client import submit_to_gemini, build_prompt

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
    parser.add_argument("--chat-id", required=True, help="Telegram chat ID")
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
            result = await analyze_job(job, profile, args.chat_id, args.browser_path)
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
```

- [ ] **Step 2: Verify syntax**

Run: `python3 -m py_compile analyzer.py`
Expected: No output (success)

- [ ] **Step 3: Commit**

```bash
git add analyzer.py
git commit -m "feat: add main analyzer script with Gemini and Telegram integration"
```

---

## Task 7: Test Suite

**Files:**
- Create: `tests/test_analyzer.py`

```python
import pytest
from profile import load_profile
from job_loader import load_jobs, count_jobs
from telegram_notify import format_job_analysis, parse_gemini_response

def test_load_profile(tmp_path):
    p = tmp_path / "profile.txt"
    p.write_text("Python developer with 5 years experience")
    assert load_profile(str(p)) == "Python developer with 5 years experience"

def test_load_jobs(tmp_path):
    f = tmp_path / "jobs.jsonl"
    f.write_text('{"title": "Dev", "company": "Acme"}\n{"title": "Eng", "company": "Beta"}')
    jobs = list(load_jobs(str(f)))
    assert len(jobs) == 2
    assert jobs[0]['title'] == 'Dev'

def test_parse_gemini_response():
    text = """1. FIT SCORE: 8/10
2. WHY GOOD: Good match for skills
3. WHY BAD: Low salary
4. RECOMMENDATION: Apply"""
    result = parse_gemini_response(text)
    assert result['score'] == '8/10'
    assert result['recommendation'] == 'Apply'

def test_format_job_analysis():
    job = {'title': 'Dev', 'company': 'Acme', 'location': 'NYC', 'job_url': 'http://x.com'}
    analysis = {'score': '9/10', 'why_good': 'Great', 'why_bad': 'None', 'recommendation': 'Apply'}
    msg = format_job_analysis(job, analysis)
    assert 'Dev' in msg
    assert 'Acme' in msg
    assert '9/10' in msg
```

- [ ] **Step 1: Create tests/test_analyzer.py**

```python
import pytest
from profile import load_profile
from job_loader import load_jobs, count_jobs
from telegram_notify import format_job_analysis, parse_gemini_response

def test_load_profile(tmp_path):
    """Test profile loading."""
    p = tmp_path / "profile.txt"
    p.write_text("Python developer with 5 years experience")
    assert load_profile(str(p)) == "Python developer with 5 years experience"

def test_load_profile_empty(tmp_path):
    """Test empty profile raises error? Or returns empty string?"""
    p = tmp_path / "profile.txt"
    p.write_text("")
    # Empty profile is still valid
    assert load_profile(str(p)) == ""

def test_load_jobs_single(tmp_path):
    """Test loading single job."""
    f = tmp_path / "jobs.jsonl"
    f.write_text('{"title": "Dev", "company": "Acme"}')
    jobs = list(load_jobs(str(f)))
    assert len(jobs) == 1
    assert jobs[0]['title'] == 'Dev'

def test_load_jobs_multiple(tmp_path):
    """Test loading multiple jobs."""
    f = tmp_path / "jobs.jsonl"
    f.write_text('{"title": "Dev", "company": "Acme"}\n{"title": "Eng", "company": "Beta"}')
    jobs = list(load_jobs(str(f)))
    assert len(jobs) == 2
    assert jobs[0]['title'] == 'Dev'
    assert jobs[1]['title'] == 'Eng'

def test_load_jobs_ignores_invalid_json(tmp_path):
    """Test that invalid JSON lines are skipped."""
    f = tmp_path / "jobs.jsonl"
    f.write_text('{"title": "Dev"}\ninvalid json\n{"title": "Eng"}')
    jobs = list(load_jobs(str(f)))
    assert len(jobs) == 2

def test_count_jobs(tmp_path):
    """Test job counting."""
    f = tmp_path / "jobs.jsonl"
    f.write_text('{"title": "Dev"}\n{"title": "Eng"}\n{"title": "QA"}')
    assert count_jobs(str(f)) == 3

def test_parse_gemini_response_complete():
    """Test parsing a complete Gemini response."""
    text = """1. FIT SCORE: 8/10
2. WHY GOOD: Great match for my Python skills
3. WHY BAD: Salary is below my期望
4. RECOMMENDATION: Apply"""
    result = parse_gemini_response(text)
    assert result['score'] == '8/10'
    assert 'Python skills' in result['why_good']
    assert 'Salary' in result['why_bad']
    assert result['recommendation'] == 'Apply'

def test_parse_gemini_response_partial():
    """Test parsing response with missing fields."""
    text = """1. FIT SCORE: 7/10
3. WHY BAD: Not a good fit"""
    result = parse_gemini_response(text)
    assert result['score'] == '7/10'
    assert result['why_good'] == 'N/A'
    assert 'Not a good fit' in result['why_bad']

def test_format_job_analysis():
    """Test formatting job analysis as Telegram message."""
    job = {
        'title': 'Senior Python Developer',
        'company': 'TechCorp',
        'location': 'San Francisco, CA',
        'job_url': 'https://example.com/job/123'
    }
    analysis = {
        'score': '9/10',
        'why_good': 'Perfect match for my Django and AWS experience',
        'why_bad': 'Might be too senior for my level',
        'recommendation': 'Apply'
    }
    msg = format_job_analysis(job, analysis)

    assert 'Senior Python Developer' in msg
    assert 'TechCorp' in msg
    assert 'San Francisco' in msg
    assert '9/10' in msg
    assert 'Django and AWS' in msg
    assert 'Apply' in msg
```

- [ ] **Step 2: Run tests**

Run: `cd /home/can/Desktop/job && python3 -m pytest tests/test_analyzer.py -v`
Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
git add tests/test_analyzer.py
git commit -m "test: add unit tests for job analyzer"
```

---

## Execution Options

**Plan complete and saved to `docs/superpowers/plans/2026-04-26-job-analyzer-plan.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**

---

## Usage Commands (After Implementation)

```bash
# 1. Create profile.txt with your background
echo "Your skills, experience, requirements here" > profile.txt

# 2. Run analyzer
python3 analyzer.py --chat-id YOUR_CHAT_ID --jobs jobs.jsonl --profile profile.txt

# 3. Dry run (limit to 1 job)
python3 analyzer.py --chat-id YOUR_CHAT_ID --limit 1

# 4. With custom browser path
python3 analyzer.py --chat-id YOUR_CHAT_ID --browser-path /path/to/browser/data
```

**Note:** You need to provide your Telegram chat ID. Get it by messaging @userinfobot on Telegram.