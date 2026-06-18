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
CAN AHMET ÖZGÜVEN
DATA SCIENTIST
Ankara | 05396879669 | canahmetozguven@gmail.com

SUMMARY
Data Scientist with a unique background in Psychological Counseling, blending deep analytical skills with an understanding of human behavior. Specializes in Health & Benefits Technology, transforming complex clinical and behavioral data into production-grade signals that drive user engagement and wellness outcomes. Proficient in building end-to-end ELT processes in Google BigQuery, integrating Generative AI (LLMs) into production pipelines, and accelerating development workflows using AI-native tools (Cursor, Claude). Experienced in remote, international cross-functional teams.

PROFESSIONAL EXPERIENCE
Data Scientist | Well | Remote (US-Based) | Nov 2023 - Present
- Machine Learning & Model Optimization: Engineered features for the Consumer Action Engagement Model, utilizing behavioral signals to achieve a 3% improvement in model performance. Integrated MLflow into the training pipeline for robust experiment tracking, model registry, and reproducible lifecycle management.
- Pipeline Architecture & Optimization: Refactored core consumer data pipelines to align real-time PostgreSQL transactional data with BigQuery, achieving a 3-5% performance improvement. Designed a sampling-based testing framework that validates pipeline logic.
- Clinical Data Modeling & Feature Engineering: Designed and maintained production-grade "Fact" tables in Google BigQuery and SQL to identify clinical signals (GLP-1 weight loss usage, nicotine dependence). These models power personalized member coaching and downstream analytics.
- GenAI Integration & AI-Native Workflows: Integrated Google Gemini (GenAI SDK) into production pipelines for structured text generation. Leveraged AI-driven development tools (Cursor, Claude, Gemini CLI) for code refactoring.
- Enterprise Program Logic: Spearheaded data logic implementation for Premium Reduction and Wellness Incentive programs for major enterprise clients (Bank of America, UNC Health, USAA).

Junior Python Developer | Smart Maple | Ankara, Türkiye | Oct 2022 - Nov 2023
- Created end-to-end ETL/ELT, visualization, and cleaning pipelines using Python and SQL.
- Employed web scraping techniques (Scrapy, Selenium, Playwright) to acquire external data.
- Improved key business metrics by 10% through a new SQL data pipeline.
- Designed and built a data visualization dashboard for data-driven business decisions.

EDUCATION
Bachelor's Degree in Psychological Counseling and Guidance | Kastamonu University | 2016 - 2021
- GPA: 3.44/4.00 | ERASMUS+ Romania

Python Data Science Career Track | DataCamp
- Intensive bootcamp focused on data analysis and modeling.

SKILLS
- Programming: Python, SQL
- ML: Machine Learning, Deep Learning, Generative AI, Data Analysis, Web Scraping, MLflow
- Databases: PostgreSQL, Google BigQuery, MS SQL, NoSQL

LANGUAGES
Turkish — Native | English — Full Professional Proficiency

JOB INFO:
Title: {title}
Company: {company}
Location: {location}
URL: {url}

Description:
{description}

Guidance:
- Score fit strictly using evidence from the profile and description only. Do not inflate scores for vague overlap.
- **Data-role boost:** For any job whose title contains one of the following, you MUST score it 6+/10 even if only loosely or tangentially related. This is a mandatory floor, not a suggestion: data engineer, data analyst, analytics, BI analyst, business analyst, ML engineer, ML ops, AI engineer, LLM engineer, deep learning, NLP engineer, data infrastructure, ETL/data warehouse, data platform, BI engineer.
- **Data Science priority:** If the job title contains "Data Science" or "Data Scientist", score it 9/10 or 10/10. **Exception:** If hard dealbreakers exist, reduce the score but never go below 6+/10 — this is a mandatory minimum floor. Always flag dealbreakers prominently in WHY BAD.
- **Strategic Edge:** Flag in WHY GOOD if the role involves HealthTech, behavioral analytics, LLM integration, or international/remote setups where my unique background is an asset.
- Make WHY GOOD concise: short bullets or phrases explaining why this is worth applying to now.
- Make WHY BAD concise: include gaps, dealbreakers, mandatory language requirements, visa/relocation hurdles, or missing tech stacks.
- RECOMMENDATION must be exactly one of Apply, Review, or Skip. Add one short next step after the keyword if possible, like "Apply — tailor resume" or "Review — confirm visa sponsorship".
- Keep the response brief and Telegram-friendly.
- Do not use JSON or extra headings.

Respond with EXACTLY this format and choose only one recommendation action:
FIT SCORE: X/10
WHY GOOD: ...
WHY BAD: ...
RECOMMENDATION: <Apply|Review|Skip> — <one short next step>"""


# Big Tech 7 — top tech companies frequently hiring data scientists globally.
# Match is case-insensitive substring against the company field. Keys are the
# canonical company name; values are aliases that map to that company.
BIG_TECH_COMPANIES: dict[str, list[str]] = {
    "Apple":     ["Apple", "Apple Inc"],
    "Microsoft": ["Microsoft", "Microsoft Corporation"],
    "Google":    ["Google", "Alphabet", "YouTube", "Waymo", "DeepMind", "Google LLC"],
    "Amazon":    ["Amazon", "Amazon Web Services", "AWS"],
    "Meta":      ["Meta", "Meta Platforms", "Facebook"],
    "Nvidia":    ["Nvidia", "NVIDIA", "Nvidia Corporation"],
    "Tesla":     ["Tesla", "Tesla Motors"],
}

def match_big_tech(company: str | None) -> str | None:
    """Return canonical Big Tech company name if `company` matches an alias, else None.

    Case-insensitive substring match. None and empty string return None.
    """
    if not company:
        return None
    company_lower = company.lower()
    for canonical, aliases in BIG_TECH_COMPANIES.items():
        if any(alias.lower() in company_lower for alias in aliases):
            return canonical
    return None
