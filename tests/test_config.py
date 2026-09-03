"""Unit tests for config.py helpers."""

import pytest

from ai_job_tracker.config import (
    BIG_TECH_COMPANIES,
    Settings,
    match_big_tech,
    require_telegram_credentials,
)


def test_require_telegram_credentials_returns_stripped_values():
    assert require_telegram_credentials(" token ", " chat ") == ("token", "chat")


@pytest.mark.parametrize(
    "token, chat_id, missing_name",
    [
        (None, "123", "TELEGRAM_BOT_TOKEN"),
        ("token", None, "TELEGRAM_CHAT_ID"),
        (" ", "123", "TELEGRAM_BOT_TOKEN"),
        ("token", " ", "TELEGRAM_CHAT_ID"),
    ],
)
def test_require_telegram_credentials_rejects_missing_values(token, chat_id, missing_name):
    with pytest.raises(ValueError, match=missing_name):
        require_telegram_credentials(token, chat_id)


def test_match_big_tech_canonical():
    assert match_big_tech("Apple") == "Apple"
    assert match_big_tech("Microsoft") == "Microsoft"
    assert match_big_tech("Google") == "Google"
    assert match_big_tech("Amazon") == "Amazon"
    assert match_big_tech("Meta") == "Meta"
    assert match_big_tech("Nvidia") == "Nvidia"
    assert match_big_tech("Tesla") == "Tesla"


def test_match_big_tech_aliases():
    assert match_big_tech("Meta Platforms") == "Meta"
    assert match_big_tech("Facebook") == "Meta"
    assert match_big_tech("Amazon Web Services") == "Amazon"
    assert match_big_tech("AWS") == "Amazon"
    assert match_big_tech("Alphabet") == "Google"
    assert match_big_tech("YouTube") == "Google"
    assert match_big_tech("DeepMind") == "Google"
    assert match_big_tech("NVIDIA") == "Nvidia"
    assert match_big_tech("Tesla Motors") == "Tesla"


def test_match_big_tech_case_insensitive():
    assert match_big_tech("apple") == "Apple"
    assert match_big_tech("META") == "Meta"
    assert match_big_tech("amazon web services") == "Amazon"


def test_match_big_tech_no_match():
    assert match_big_tech("Acme Co") is None
    assert match_big_tech("Random Startup") is None
    assert match_big_tech("Jobgether") is None


def test_match_big_tech_none_and_empty():
    assert match_big_tech(None) is None
    assert match_big_tech("") is None


def test_match_big_tech_partial_match():
    """Substring matching: a company with 'Tesla' anywhere in its name matches."""
    assert match_big_tech("Tesla Motors Inc") == "Tesla"
    assert match_big_tech("Microsoft Corporation") == "Microsoft"


def test_big_tech_companies_has_all_seven():
    assert set(BIG_TECH_COMPANIES.keys()) == {
        "Apple", "Microsoft", "Google", "Amazon", "Meta", "Nvidia", "Tesla"
    }


def test_settings_defaults_apply_without_env(monkeypatch, tmp_path):
    for key in ("PROFILE_FILE", "JOBS_INPUT_FILE", "BROWSER_PROFILE_PATH", "TELEGRAM_BOT_TOKEN"):
        monkeypatch.delenv(key, raising=False)

    loaded = Settings(_env_file=tmp_path / "missing.env")

    assert loaded.profile_file == "profile.txt"
    assert loaded.jobs_input_file == "jobs.jsonl"
    assert loaded.analysis_output_file == "analysis_results.jsonl"
    assert loaded.gemini_url == "https://gemini.google.com/app"
    assert loaded.telegram_bot_token is None
    assert loaded.gemini_browser_executable is None


def test_settings_read_from_env_file(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "TELEGRAM_BOT_TOKEN=file-token\n"
        "PROFILE_FILE=cv.txt\n"
        "GEMINI_URL=https://example.test/app\n"
    )

    loaded = Settings(_env_file=env_file)

    assert loaded.telegram_bot_token == "file-token"
    assert loaded.profile_file == "cv.txt"
    assert loaded.gemini_url == "https://example.test/app"


def test_process_env_wins_over_env_file(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("PROFILE_FILE=from-file.txt\n")
    monkeypatch.setenv("PROFILE_FILE", "from-environ.txt")

    assert Settings(_env_file=env_file).profile_file == "from-environ.txt"


@pytest.mark.parametrize("blank", ["", "   "])
def test_blank_value_is_treated_as_unset(monkeypatch, tmp_path, blank):
    """`.env.example` ships blank keys; those must not override defaults."""
    monkeypatch.setenv("PROFILE_FILE", blank)
    monkeypatch.setenv("BROWSER_PROFILE_PATH", blank)

    loaded = Settings(_env_file=tmp_path / "missing.env")

    assert loaded.profile_file == "profile.txt"
    assert loaded.browser_profile_path.endswith("Brave/User Data")


def test_settings_ignores_unrelated_env_vars(monkeypatch, tmp_path):
    monkeypatch.setenv("SOME_UNRELATED_KEY", "value")

    assert Settings(_env_file=tmp_path / "missing.env").profile_file == "profile.txt"
