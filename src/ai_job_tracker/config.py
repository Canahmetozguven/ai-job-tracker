"""Configuration for job analyzer.

Every operator-tunable value lives on :class:`Settings` and is read from the
environment or a `.env` file. Field names map to their upper-case env var
(``profile_file`` <- ``PROFILE_FILE``), so `.env.example` documents the full
surface. Nothing here is hard-coded per-machine.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Operator-tunable settings, sourced from the environment or `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Telegram bot that sends messages. Both credentials stay optional here so
    # that scrape-only entry points start without them; require_telegram_credentials
    # is the trust boundary that fails before anything is sent.
    telegram_bot_token: str | None = None
    # Telegram destination. There is deliberately no repository-owned fallback:
    # operators must choose the destination in their environment or on the CLI.
    telegram_chat_id: str | None = None

    # Which analysis backend to use: "api" (pydantic-ai) or "browser" (Playwright).
    # Install the matching extra: pip install 'ai-job-tracker[api]' or '[browser]'.
    analysis_backend: Literal["api", "browser"] = "api"

    # --- API backend settings ---
    ai_api_key: str | None = None
    ai_model: str = "google:gemini-2.5-flash"

    # --- Browser backend settings ---
    browser_profile_path: str = ""
    gemini_browser_executable: str | None = None
    gemini_url: str = "https://gemini.google.com/app"

    # Default file paths, relative to the working directory the CLI runs in.
    profile_file: str = "profile.txt"
    jobs_input_file: str = "jobs.jsonl"
    analysis_output_file: str = "analysis_results.jsonl"

    @model_validator(mode="before")
    @classmethod
    def _blank_means_unset(cls, data: Any) -> Any:
        """Drop blank values so field defaults apply.

        `.env.example` ships keys with empty values (``TELEGRAM_BOT_TOKEN=``),
        and the previous ``os.getenv(...) or default`` idiom treated those as
        absent. Removing the key here preserves that, rather than letting an
        empty string override a real default.
        """
        if isinstance(data, dict):
            return {
                key: value
                for key, value in data.items()
                if not (isinstance(value, str) and not value.strip())
            }
        return data


settings = Settings()


def require_telegram_credentials(
    token: str | None,
    chat_id: str | None,
) -> tuple[str, str]:
    """Return configured Telegram credentials or fail before sending."""
    missing = []
    if not token or not token.strip():
        missing.append("TELEGRAM_BOT_TOKEN")
    if not chat_id or not chat_id.strip():
        missing.append("TELEGRAM_CHAT_ID (or --chat-id)")
    if missing:
        raise ValueError(f"Missing required Telegram configuration: {', '.join(missing)}")
    return token.strip(), chat_id.strip()

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
- Score fit strictly using evidence from the profile and description only. Do not inflate scores for vague overlap.
- **Data-role boost:** For any job whose title contains one of the following, you MUST score it 6+/10 even if only loosely or tangentially related. This is a mandatory floor, not a suggestion: data engineer, data analyst, analytics, BI analyst, business analyst, ML engineer, ML ops, AI engineer, LLM engineer, deep learning, NLP engineer, data infrastructure, ETL/data warehouse, data platform, BI engineer.
- **Data Science priority:** If the job title contains "Data Science" or "Data Scientist", score it 9/10 or 10/10. **Exception:** If hard dealbreakers exist, reduce the score but never go below 6+/10 — this is a mandatory minimum floor. Always flag dealbreakers prominently in why_bad.
- **Strategic Edge:** Flag in why_good if the role involves HealthTech, behavioral analytics, LLM integration, or international/remote setups where my unique background is an asset.
- Make why_good concise: short bullets or phrases explaining why this is worth applying to now.
- Make why_bad concise: include gaps, dealbreakers, mandatory language requirements, visa/relocation hurdles, or missing tech stacks.
- recommendation must be exactly one of Apply, Review, or Skip. Add one short next step after the keyword if possible, like "Apply — tailor resume" or "Review — confirm visa sponsorship"."""

class AnalysisResult(BaseModel):
    score: str = Field(description="Fit score in the format X/10, e.g. '8/10'", pattern=r"^(10|[1-9])/10$")
    why_good: str = Field(description="Concise reasons why this job is a good fit")
    why_bad: str = Field(description="Concise reasons why this job is not a good fit")
    recommendation: str = Field(
        description="One of 'Apply', 'Review', or 'Skip', optionally followed by a dash and a short next step",
        pattern=r"^(Apply|Review|Skip)\b",
    )


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
