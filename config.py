"""Configuration for job analyzer."""

# Telegram Bot Token (bot that sends messages)
TELEGRAM_BOT_TOKEN = "8647111790:AAEkQaOy9JbqYVXRfDCYBHhnJS97VzHif_w"

# Browser Profile Path (Brave backup with authenticated session)
BROWSER_PROFILE_PATH = "USER_INFO_BACKUP_DESKTOP-MR1KOEH/Brave/User Data"

# Default file paths
PROFILE_FILE = "profile.txt"
JOBS_INPUT_FILE = "jobs.jsonl"
ANALYSIS_OUTPUT_FILE = "analysis_results.jsonl"

# Gemini settings
GEMINI_URL = "https://gemini.google.com/app"

# Default Telegram chat ID (override with --chat-id argument)
DEFAULT_CHAT_ID = "1949164657"

# Prompt template for Gemini analysis
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