"""LLM dispatch for job analysis — routes to the configured backend."""

from ai_job_tracker.config import settings

RETRY_DELAYS = {"api": 5, "browser": 30}
INTER_JOB_DELAYS = {"api": 0, "browser": 8}


def get_retry_delay() -> int:
    return RETRY_DELAYS.get(settings.analysis_backend, 5)


def get_inter_job_delay() -> int:
    return INTER_JOB_DELAYS.get(settings.analysis_backend, 0)


def parse_score(score_str: str) -> int:
    try:
        return int(score_str.split("/")[0])
    except (ValueError, IndexError):
        return 0


async def analyze_job_posting(prompt: str) -> dict:
    """Submit a prompt to the configured backend and return structured analysis dict."""
    if settings.analysis_backend == "api":
        return await _analyze_via_api(prompt)
    from ai_job_tracker.gemini_client import analyze_via_browser

    return await analyze_via_browser(prompt)


async def _analyze_via_api(prompt: str) -> dict:
    try:
        from pydantic_ai import Agent
        from pydantic_ai.models import infer_model
        from pydantic_ai.providers import infer_provider_class
    except ImportError:
        raise RuntimeError(
            "API backend requires pydantic-ai. Install: pip install 'ai-job-tracker[api]'"
        ) from None

    if not settings.ai_api_key:
        raise RuntimeError(
            "AI_API_KEY is required. Set it in .env — see .env.example for provider-specific examples."
        )

    from ai_job_tracker.config import AnalysisResult

    model = infer_model(
        settings.ai_model,
        provider_factory=lambda name: infer_provider_class(name)(api_key=settings.ai_api_key),
    )
    agent = Agent(model, output_type=AnalysisResult)
    result = await agent.run(prompt)
    return result.output.model_dump()


def _description_to_text(value) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, str):
        return value
    if isinstance(value, float):
        return "N/A"
    return str(value)


def build_prompt(profile: str, job: dict) -> str:
    """Build prompt from profile and job data."""
    from ai_job_tracker.config import PROMPT_TEMPLATE

    return PROMPT_TEMPLATE.format(
        profile=profile,
        title=job.get("title", "N/A") or "N/A",
        company=job.get("company", "N/A") or "N/A",
        location=job.get("location", "N/A") or "N/A",
        url=job.get("job_url", "N/A") or "N/A",
        description=_description_to_text(job.get("description"))[:2000],
    )
