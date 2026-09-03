"""Tests for prompt building — the profile must reach the prompt."""

from gemini_client import build_prompt

JOB = {
    "title": "Data Scientist",
    "company": "Acme",
    "location": "Remote",
    "job_url": "https://example.com/1",
    "description": "Build models.",
}


def test_prompt_contains_profile_text():
    profile = "JANE DOE\nDATA SCIENTIST\nSkills: Python, SQL"
    assert profile in build_prompt(profile, JOB)


def test_distinct_profiles_produce_distinct_prompts():
    assert build_prompt("profile A", JOB) != build_prompt("profile B", JOB)


def test_template_has_no_embedded_cv():
    """A prompt built from an empty profile must not carry anyone's CV."""
    prompt = build_prompt("", JOB).lower()
    for leak in ("@gmail.com", "@example.com", "professional experience", "education"):
        assert leak not in prompt


def test_no_operator_identity_in_application_code():
    """Config must not ship anyone's CV, contact details, or machine paths."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    for name in ("config.py", "analyzer.py"):
        source = (root / name).read_text()
        for leak in ("1949164657", "MR1KOEH", "@gmail.com", "05396879669"):
            assert leak not in source, f"{name} still embeds {leak}"
