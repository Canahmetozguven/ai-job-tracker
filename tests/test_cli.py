"""Tests for the `job` Typer app that fronts every pipeline step."""

import copy
import json
import tomllib
from importlib import import_module
from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

from ai_job_tracker import analyzer, cli as cli_module, proxy_scraper, run_daily, scraper, validate_proxies
from ai_job_tracker.cli import app

from conftest import CLI_ENV, plain

runner = CliRunner(env=CLI_ENV)

COMMANDS = ["scrape", "analyze", "daily", "career", "proxies", "validate-proxies"]


def test_root_help_lists_every_command():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for name in COMMANDS:
        assert name in plain(result.output)


def test_bare_invocation_shows_help_instead_of_running():
    result = runner.invoke(app, [])
    assert result.exit_code != 0
    assert "Commands" in plain(result.output)


@pytest.mark.parametrize("command", COMMANDS)
def test_each_command_help_exits_clean(command):
    result = runner.invoke(app, [command, "--help"])
    assert result.exit_code == 0


def test_unknown_command_is_rejected():
    assert runner.invoke(app, ["nope"]).exit_code != 0


def test_scrape_passes_flags_through_to_core():
    with patch.object(scraper, "run_cli") as run_cli:
        result = runner.invoke(app, [
            "scrape", "--query", "data scientist", "--location", "Ankara",
            "--source", "2", "--limit", "5", "--output", "o.jsonl",
            "--hours", "3", "--append", "--no-proxy", "--interval", "45",
        ])
    assert result.exit_code == 0, plain(result.output)
    kwargs = run_cli.call_args.kwargs
    assert kwargs["query"] == "data scientist"
    assert kwargs["location"] == "Ankara"
    assert kwargs["source"] == 2
    assert kwargs["limit"] == 5
    assert kwargs["output"] == "o.jsonl"
    assert kwargs["hours_old"] == 3
    assert kwargs["append_mode"] is True
    assert kwargs["no_proxy"] is True
    assert kwargs["interval"] == 45


def test_scrape_big_tech_skips_the_location_prompt():
    """--big-tech searches globally, so it must run without stdin."""
    with patch.object(scraper, "run_cli") as run_cli:
        result = runner.invoke(app, ["scrape", "--query", "ds", "--big-tech"])
    assert result.exit_code == 0, plain(result.output)
    assert run_cli.call_args.kwargs["big_tech"] is True


def test_scrape_rejects_source_outside_range():
    assert runner.invoke(app, ["scrape", "--query", "ds", "--source", "9"]).exit_code != 0


def test_scrape_interactive_binds_every_option():
    """Regression: the old no-args branch never bound no_proxy/hours_old/
    specific_proxy, so it raised UnboundLocalError before scraping."""
    answers = iter(["data scientist", "Ankara", "1", "10", "out.jsonl", "n", "n"])
    with patch("builtins.input", lambda *_: next(answers)):
        options = scraper.prompt_for_options()

    for key in ("query", "location", "source", "limit", "output", "append_mode",
                "daemon", "interval", "country", "big_tech",
                "hours_old", "no_proxy", "specific_proxy"):
        assert key in options, f"prompt_for_options() must bind {key}"

    # run_cli accepts exactly what prompt_for_options produces.
    with patch.object(scraper, "load_proxies", return_value=[]), \
         patch.object(scraper, "read_existing_jobs", return_value=set()), \
         patch.object(scraper, "run_scrape", return_value=[]), \
         patch.object(scraper, "append_jobs_jsonl", return_value=0):
        scraper.run_cli(**options)


def test_analyze_without_telegram_credentials_fails_cleanly(monkeypatch):
    monkeypatch.setattr("ai_job_tracker.cli.settings.telegram_bot_token", None)
    monkeypatch.setattr("ai_job_tracker.cli.settings.telegram_chat_id", None)

    result = runner.invoke(app, ["analyze"])

    assert result.exit_code != 0
    assert "TELEGRAM_BOT_TOKEN" in plain(result.output)


@pytest.mark.parametrize(
    ("outcome", "expected_exit_code"),
    [
        ("no_jobs", 0),
        ("success", 0),
        ("partial", 0),
        ("failed", 1),
    ],
)
def test_analyze_exit_status_reflects_run_outcome(tmp_path, mocker, outcome, expected_exit_code):
    profile_path = tmp_path / "profile.txt"
    jobs_path = tmp_path / "jobs.jsonl"
    output_path = tmp_path / "analysis.jsonl"
    profile_path.write_text("Python developer")

    job_count = {"no_jobs": 0, "success": 1, "partial": 2, "failed": 1}[outcome]
    jobs = [{"title": f"Job {index}", "job_url": f"https://example.com/{index}"} for index in range(job_count)]
    jobs_path.write_text("".join(json.dumps(job) + "\n" for job in jobs))

    successful_result = {
        "job": jobs[0] if jobs else {},
        "analysis": {"score": "8/10", "recommendation": "Apply"},
        "gemini_response": "response",
    }
    outcomes = {
        "no_jobs": [],
        "success": [successful_result],
        "partial": [successful_result, RuntimeError("analysis failed")],
        "failed": [RuntimeError("analysis failed")],
    }
    mocker.patch.object(analyzer, "analyze_job", side_effect=outcomes[outcome])
    mocker.patch.object(analyzer.asyncio, "sleep", new=mocker.AsyncMock())
    mocker.patch.object(cli_module, "_require_telegram", return_value=("token", "chat-id"))

    result = runner.invoke(
        app,
        [
            "analyze",
            "--profile",
            str(profile_path),
            "--jobs",
            str(jobs_path),
            "--output",
            str(output_path),
            "--chat-id",
            "chat-id",
        ],
    )

    assert result.exit_code == expected_exit_code, plain(result.output)


def test_analyze_persists_error_record_before_failing(tmp_path, mocker):
    profile_path = tmp_path / "profile.txt"
    jobs_path = tmp_path / "jobs.jsonl"
    output_path = tmp_path / "analysis.jsonl"
    profile_path.write_text("Python developer")
    jobs_path.write_text(json.dumps({"title": "Broken job", "job_url": "https://example.com/broken"}) + "\n")
    mocker.patch.object(analyzer, "analyze_job", side_effect=RuntimeError("analysis failed"))
    mocker.patch.object(cli_module, "_require_telegram", return_value=("token", "chat-id"))

    result = runner.invoke(
        app,
        [
            "analyze",
            "--profile",
            str(profile_path),
            "--jobs",
            str(jobs_path),
            "--output",
            str(output_path),
            "--chat-id",
            "chat-id",
        ],
    )

    persisted_record = json.loads(output_path.read_text())
    assert result.exit_code == 1
    assert persisted_record["error"] == "analysis failed"


def test_daily_without_telegram_credentials_fails_cleanly(monkeypatch):
    monkeypatch.setattr("ai_job_tracker.cli.settings.telegram_bot_token", None)
    monkeypatch.setattr("ai_job_tracker.cli.settings.telegram_chat_id", None)

    result = runner.invoke(app, ["daily"])

    assert result.exit_code != 0
    assert "TELEGRAM_CHAT_ID" in plain(result.output)


def test_validate_proxies_requires_both_paths():
    assert runner.invoke(app, ["validate-proxies", "only-one.txt"]).exit_code != 0


def test_proxies_command_exits_zero_despite_dict_returning_core(tmp_path):
    """Regression: `job-proxies` was wired straight to a dict-returning main().

    The generated console-script launcher runs `sys.exit(app())`, so returning
    the result mapping printed it to stderr and exited 1 — schedulers read a
    successful refresh as a failure. The command must return None while
    proxy_scraper.scrape() still hands the mapping back to callers.
    """
    out = tmp_path / "p.txt"
    with patch.object(proxy_scraper, "scrape", return_value={"total": 1, "sources": {}}) as core:
        result = runner.invoke(app, ["proxies", "--source", "1", "--output", str(out)])

    assert result.exit_code == 0, plain(result.output)
    assert core.called
    # The core keeps its mapping contract for programmatic callers.
    assert core.return_value["total"] == 1


def test_entry_point_is_wired_to_the_typer_app():
    """`[project.scripts]` must target the Typer app, not a bare function.

    The generated launcher runs `sys.exit(<target>())`. A function wired
    directly leaks its return value into the exit status — which is how
    `job-proxies = "...proxy_scraper:main"` came to print its result dict and
    exit 1 on success. Going through the app keeps Click in charge of the code.
    """
    with open("pyproject.toml", "rb") as fh:
        scripts = tomllib.load(fh)["project"]["scripts"]

    assert scripts == {"job": "ai_job_tracker.cli:app"}

    module_name, _, attr = scripts["job"].partition(":")
    target = getattr(import_module(module_name), attr)
    assert isinstance(target, typer.Typer)


def test_daily_threads_configured_analysis_output_through_accounting(monkeypatch):
    """The child's --output and the summary's accounting must be the same path.

    ANALYSIS_OUTPUT_FILE became configurable in the settings commit, but the
    daily pipeline still counted the literal analysis_results.jsonl. With a
    custom path the summary saw no new records and could report success while
    the configured file held processed jobs or failures.
    """
    monkeypatch.setattr(run_daily.settings, "analysis_output_file", "custom_results.jsonl")

    command_calls = []
    counted, read = [], []

    monkeypatch.setattr(run_daily, "validate_proxies", lambda: ["1.2.3.4:8080"])
    monkeypatch.setattr(run_daily, "print_summary", lambda **_: None)
    monkeypatch.setattr(run_daily, "_update_pass_summary", lambda *a, **k: None)
    monkeypatch.setattr(
        run_daily,
        "run_command",
        lambda cmd, desc, **kwargs: command_calls.append((cmd, kwargs)) or True,
    )
    monkeypatch.setattr(run_daily, "count_jsonl_lines", lambda p: counted.append(p) or 0)
    monkeypatch.setattr(run_daily, "read_jsonl_records", lambda p, n: read.append(p) or [])
    monkeypatch.setattr(run_daily, "summarize_analysis_results", lambda records, ok: {})

    run_daily.run("chat-123")

    analyze_argv, analyze_kwargs = next(call for call in command_calls if "analyze" in call[0])
    assert "--output" in analyze_argv
    assert analyze_argv[analyze_argv.index("--output") + 1] == "custom_results.jsonl"
    assert analyze_kwargs["retries"] == 1
    assert counted == ["custom_results.jsonl"]
    assert read == ["custom_results.jsonl"]


def test_daily_reports_failed_analyzer_exit_with_persisted_error_records(monkeypatch):
    original_run_summary = copy.deepcopy(run_daily.run_summary)
    run_daily.run_summary = {
        "started_at": None,
        "proxy_validation": {"total": 1, "working": 1, "selected": None},
        "scrape": {
            "turkey_local": {"found": 0, "new": 0, "status": "not_run"},
            "big_tech_global": {"found": 0, "new": 0, "status": "not_run"},
            "career_site": {"found": 0, "new": 0, "status": "not_run"},
        },
        "analyze": {"processed": 0, "succeeded": 0, "failed": 0, "status": "not_run", "error_summary": None},
        "errors": [],
    }
    error_record = {"job": {"job_url": "https://failed.example/job"}, "error": "analysis failed"}

    monkeypatch.setattr(run_daily, "validate_proxies", lambda: ["1.2.3.4:8080"])
    monkeypatch.setattr(run_daily, "print_summary", lambda **_: None)
    monkeypatch.setattr(run_daily, "_update_pass_summary", lambda *_: None)
    monkeypatch.setattr(run_daily, "run_command", lambda command, *_args, **_kwargs: "analyze" not in command)
    monkeypatch.setattr(run_daily, "count_jsonl_lines", lambda _path: 0)
    monkeypatch.setattr(run_daily, "read_jsonl_records", lambda _path, _start: [error_record])

    try:
        run_daily.run("chat-id")

        assert run_daily.run_summary["analyze"] == {
            "processed": 1,
            "succeeded": 0,
            "failed": 1,
            "status": "failed",
            "error_summary": "All 1 jobs failed. First error: analysis failed",
        }
        assert run_daily.run_summary["errors"] == [
            "All 1 jobs failed. First error: analysis failed",
            "Analysis failed",
        ]
    finally:
        run_daily.run_summary = original_run_summary
