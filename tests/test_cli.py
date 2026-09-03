"""Tests for the `job` Typer app that fronts every pipeline step."""

import tomllib
from importlib import import_module
from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

from ai_job_tracker import proxy_scraper, scraper, validate_proxies
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
