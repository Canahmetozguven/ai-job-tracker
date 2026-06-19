"""Unit tests for career_scrapers package."""

import urllib.error
from unittest.mock import patch, MagicMock

import pytest

from career_scrapers import SCRAPERS
from career_scrapers.amazon import AmazonScraper
from career_scrapers.base import BaseCareerScraper


# --- registry ---


def test_registry_contains_amazon():
    assert "Amazon" in SCRAPERS
    assert SCRAPERS["Amazon"] is AmazonScraper


# --- BaseCareerScraper init ---


def test_base_subclass_requires_name():
    class Bad(BaseCareerScraper):
        base_url = "https://example.com"

    with pytest.raises(ValueError, match="must set `name`"):
        Bad()


def test_base_subclass_requires_base_url():
    class Bad(BaseCareerScraper):
        name = "Bad"

    with pytest.raises(ValueError, match="must set `base_url`"):
        Bad()


def test_base_subclass_init_succeeds():
    s = AmazonScraper()
    assert s.name == "Amazon"
    assert s.base_url == "https://amazon.jobs"
    assert s.proxy is None


# --- _make_record ---


def test_make_record_fills_source_pass_and_company():
    s = AmazonScraper()
    rec = s._make_record(
        title="DS", company="Amazon", location="Seattle",
        job_url="https://amazon.jobs/j/123",
    )
    assert rec["source_pass"] == "career_site"
    assert rec["source_company"] == "Amazon"
    assert rec["source"] == "amazon_career"
    assert rec["title"] == "DS"
    assert rec["date_posted"] == "unknown"
    assert rec["description"] is None
    assert rec["is_remote"] is None
    assert rec["salary"] is None


def test_make_record_uses_explicit_source():
    s = AmazonScraper()
    rec = s._make_record(
        title="DS", company="Amazon", location="X",
        job_url="https://example.com/1", source="custom_tag",
    )
    assert rec["source"] == "custom_tag"


def test_make_record_preserves_explicit_date_posted():
    s = AmazonScraper()
    rec = s._make_record(
        title="DS", company="Amazon", location="X",
        job_url="https://example.com/1", date_posted="2026-01-01",
    )
    assert rec["date_posted"] == "2026-01-01"


# --- _throttle ---


def test_throttle_sleeps_to_meet_rate_limit():
    import time
    s = AmazonScraper()
    s.rate_limit_seconds = 0.1
    s._throttle()  # first call: no sleep
    t0 = time.monotonic()
    s._throttle()  # second call: should sleep ~0.1s
    elapsed = time.monotonic() - t0
    assert elapsed >= 0.09


# --- _get retry ---


def test_get_retries_on_5xx_then_succeeds():
    s = AmazonScraper()
    call_count = {"n": 0}

    def fake_urlopen(req, timeout):
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise urllib.error.HTTPError(req.full_url, 503, "Service Unavailable", {}, None)
        m = MagicMock()
        m.__enter__ = lambda self: self
        m.__exit__ = lambda self, *a: None
        m.read.return_value = b'{"ok": true}'
        return m

    with patch("career_scrapers.base.urllib.request.urlopen", side_effect=fake_urlopen):
        body = s._get("https://example.com/api")
    assert body == b'{"ok": true}'
    assert call_count["n"] == 3


def test_get_raises_after_max_retries():
    s = AmazonScraper()
    s.max_retries = 2

    def always_503(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 503, "Service Unavailable", {}, None)

    with patch("career_scrapers.base.urllib.request.urlopen", side_effect=always_503):
        with pytest.raises(urllib.error.HTTPError):
            s._get("https://example.com/api")


def test_get_does_not_retry_on_404():
    s = AmazonScraper()
    call_count = {"n": 0}

    def always_404(req, timeout):
        call_count["n"] += 1
        raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)

    with patch("career_scrapers.base.urllib.request.urlopen", side_effect=always_404):
        with pytest.raises(urllib.error.HTTPError):
            s._get("https://example.com/api")
    assert call_count["n"] == 1  # no retry
