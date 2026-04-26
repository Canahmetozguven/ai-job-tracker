"""Configuration for job analyzer."""

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = "8647111790:AAEkQaOy9JbqYVXRfDCYBHhnJS97VzHif_w"

# Browser Profile Path (Brave backup from other computer)
BROWSER_PROFILE_PATH = "USER_INFO_BACKUP_DESKTOP-MR1KOEH/Brave/User Data"

# Default paths
PROFILE_FILE = "profile.txt"  # User's profile (rename from user_profile.py on disk if needed
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