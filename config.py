"""Configuration for job analyzer."""

import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token (bot that sends messages)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Browser Profile Path (Brave backup with authenticated session)
BROWSER_PROFILE_PATH = os.getenv("BROWSER_PROFILE_PATH") or "USER_INFO_BACKUP_DESKTOP-MR1KOEH/Brave/User Data"

# Optional browser executable for Gemini automation
GEMINI_BROWSER_EXECUTABLE = os.getenv("GEMINI_BROWSER_EXECUTABLE") or None

# Default file paths
PROFILE_FILE = "profile.txt"
JOBS_INPUT_FILE = "jobs.jsonl"
ANALYSIS_OUTPUT_FILE = "analysis_results.jsonl"

# Gemini settings
GEMINI_URL = "https://gemini.google.com/app"

# Default Telegram chat ID (override with --chat-id argument)
DEFAULT_CHAT_ID = "1949164657"

# Prompt template for Gemini analysis
PROMPT_TEMPLATE = """Analyze this job posting for an actionable shortlist decision.

MY PROFILE:
{profile}

JOB INFO:
Title: {title}
Company: {company}
Location: {location}
URL: {url}

Description:
{description}

Guidance:
- Score fit strictly using evidence from the profile and description only; do not inflate scores for vague overlap.
- Make WHY GOOD concise: short bullets or phrases explaining why this is worth applying to now.
- Make WHY BAD concise: include gaps, dealbreakers, risks, missing requirements, or uncertainties.
- RECOMMENDATION must be exactly one of Apply, Review, or Skip. Add one short next step after the keyword if possible, like "Apply — tailor resume" or "Review — confirm salary".
- Keep the response brief and Telegram-friendly.
- Do not use JSON or extra headings.

Respond with EXACTLY this format and choose only one recommendation action:
FIT SCORE: X/10
WHY GOOD: ...
WHY BAD: ...
RECOMMENDATION: <Apply|Review|Skip> — <one short next step>"""
