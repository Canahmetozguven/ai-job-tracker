"""The `job` command — one entry point for every pipeline step.

All argument parsing lives here. Each command resolves its options (including
settings defaults and Telegram credential validation) and then calls a plain
typed function in the owning module, so the pipeline logic stays importable and
testable without going through Click.
"""

from __future__ import annotations

import asyncio

import typer

from ai_job_tracker import career_scraper, proxy_scraper, run_daily, scraper, validate_proxies
from ai_job_tracker.analyzer import MAX_RETRIES, run_analysis
from ai_job_tracker.config import require_telegram_credentials, settings

app = typer.Typer(
    help="Scrape, analyze, and report on data-science job postings.",
    no_args_is_help=True,
    add_completion=True,
)


def _require_telegram(chat_id: str | None) -> tuple[str, str]:
    """Validate Telegram credentials, reporting failure as a CLI error."""
    try:
        return require_telegram_credentials(settings.telegram_bot_token, chat_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--chat-id") from exc


@app.command()
def scrape(
    query: str = typer.Option(None, "--query", "-q", help="Job search query"),
    location: str = typer.Option(None, "--location", "-l", help="Location (city, state/country)"),
    country: str = typer.Option(
        "turkey",
        "--country",
        help="Country for JobSpy's country_indeed (e.g. turkey, worldwide, usa, uk)",
    ),
    big_tech: bool = typer.Option(
        False,
        "--big-tech",
        help="Post-filter to Big Tech 7. Forces a global search; ignores --location.",
    ),
    source: int = typer.Option(
        1, "--source", "-s", min=1, max=3,
        help="1=JobSpy only, 2=LinkedIn only, 3=Both with fallback",
    ),
    limit: int = typer.Option(10, "--limit", "-n", help="Results limit per source"),
    output: str = typer.Option("jobs.jsonl", "--output", "-o", help="Output file path"),
    daemon: bool = typer.Option(False, "--daemon", "-d", help="Run continuously"),
    interval: int = typer.Option(30, "--interval", "-i", help="Interval in minutes (daemon mode)"),
    hours: int = typer.Option(0, "--hours", "-H", help="Filter jobs posted in last N hours (0=disabled)"),
    append: bool = typer.Option(False, "--append", "-a", help="Append to output file (don't overwrite)"),
    no_proxy: bool = typer.Option(False, "--no-proxy", help="Disable proxy rotation"),
    proxy: str = typer.Option(None, "--proxy", help="Use a specific proxy instead of random"),
    interactive: bool = typer.Option(
        False, "--interactive", "-I", help="Prompt for options instead of reading flags"
    ),
) -> None:
    """Scrape jobs from JobSpy/LinkedIn into a JSONL file."""
    if interactive:
        scraper.run_cli(**scraper.prompt_for_options())
        return

    # --big-tech searches globally by company, so it needs no query prompt.
    if not query:
        query = typer.prompt("Enter job search query").strip()
    if not location and not big_tech:
        location = typer.prompt("Enter location (city, state/country)").strip()

    scraper.run_cli(
        query=query,
        location=location,
        country=country,
        big_tech=big_tech,
        source=source,
        limit=limit,
        output=output,
        daemon=daemon,
        interval=interval,
        hours_old=hours,
        append_mode=append,
        no_proxy=no_proxy,
        specific_proxy=proxy,
    )


@app.command()
def analyze(
    profile: str = typer.Option(None, "--profile", help="Profile file path"),
    jobs: str = typer.Option(None, "--jobs", help="Jobs input file"),
    output: str = typer.Option(None, "--output", help="Output file for results"),
    browser_path: str = typer.Option(None, "--browser-path", help="Browser profile path"),
    browser_executable: str = typer.Option(
        None,
        "--browser-executable",
        help="Optional browser executable for Gemini; falls back to common browsers or bundled Chromium",
    ),
    chat_id: str = typer.Option(
        None, "--chat-id", help="Telegram destination (defaults to TELEGRAM_CHAT_ID)"
    ),
    limit: int = typer.Option(0, "--limit", help="Limit jobs to process (0=all)"),
    hours: int = typer.Option(0, "--hours", help="Only analyze jobs posted in last N hours (0=all)"),
    skip_seen: bool = typer.Option(
        False, "--skip-seen", help="Skip jobs with successful analysis already recorded"
    ),
    retries: int = typer.Option(MAX_RETRIES, "--retries", help="Max retries per job on Gemini failure"),
) -> None:
    """Score scraped jobs against your profile with Gemini and notify Telegram."""
    # Settings supply the defaults so `.env` stays the single source; Typer
    # defaults of None mean "not given on the command line".
    token, resolved_chat_id = _require_telegram(chat_id or settings.telegram_chat_id)

    exit_code = asyncio.run(
        run_analysis(
            profile_path=profile or settings.profile_file,
            jobs_path=jobs or settings.jobs_input_file,
            output=output or settings.analysis_output_file,
            chat_id=resolved_chat_id,
            telegram_token=token,
            browser_path=browser_path or settings.browser_profile_path,
            browser_executable=browser_executable or settings.gemini_browser_executable,
            limit=limit,
            hours=hours,
            skip_seen=skip_seen,
            retries=retries,
        )
    )
    if exit_code != 0:
        raise typer.Exit(exit_code)


@app.command()
def daily(
    chat_id: str = typer.Option(
        None, "--chat-id", help="Telegram destination (defaults to TELEGRAM_CHAT_ID)"
    ),
) -> None:
    """Run the full daily pipeline: proxies, three scrape passes, then analysis."""
    _, resolved_chat_id = _require_telegram(chat_id or settings.telegram_chat_id)
    run_daily.run(resolved_chat_id)


@app.command()
def career(
    query: str = typer.Option(..., "--query", help="Job search query"),
    limit: int = typer.Option(50, "--limit", "-n", help="Max results per scraper"),
    hours: int = typer.Option(
        0, "--hours", "-H",
        help="Filter by age (hours), 0=disabled. Currently a no-op for career sites; reserved for future use.",
    ),
    output: str = typer.Option("jobs_career.jsonl", "--output", "-o", help="Output file path"),
    append: bool = typer.Option(False, "--append", "-a", help="Append to output file (don't overwrite)"),
    no_proxy: bool = typer.Option(False, "--no-proxy", help="Disable proxy rotation"),
    proxy: str = typer.Option(None, "--proxy", help="Use a specific proxy instead of random"),
) -> None:
    """Scrape the Big Tech 7 career sites directly (Apple, Microsoft, Google, Amazon, Meta, Nvidia, Tesla)."""
    # Exit 1 when every scraper errored or returned nothing.
    raise typer.Exit(
        career_scraper.run(
            query=query,
            limit=limit,
            hours=hours,
            output=output,
            append=append,
            no_proxy=no_proxy,
            proxy=proxy,
        )
    )


@app.command()
def proxies(
    source: int = typer.Option(
        None, "--source", min=1, max=3,
        help="Fetch only one source: 1=ProxyScrape, 2=Free Proxy List, 3=GeoNode",
    ),
    output: str = typer.Option(
        proxy_scraper.DEFAULT_OUTPUT_PATH, "--output", help="Output path"
    ),
) -> None:
    """Fetch free proxies from public sources."""
    proxy_scraper.scrape(source=source, output=output)


@app.command("validate-proxies")
def validate_proxies_command(
    input_file: str = typer.Argument(..., help="Proxy list to test (one host:port per line)"),
    output_file: str = typer.Argument(..., help="Where to write the working proxies"),
) -> None:
    """Test proxies in parallel and save the working ones, fastest first."""
    validate_proxies.validate(input_file, output_file)


if __name__ == "__main__":  # pragma: no cover
    app()
