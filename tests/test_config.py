"""Unit tests for config.py helpers."""

import pytest

from ai_job_tracker.config import BIG_TECH_COMPANIES, match_big_tech, require_telegram_credentials


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
