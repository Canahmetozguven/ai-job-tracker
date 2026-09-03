"""Validation helpers for parsed Gemini job analyses."""

from __future__ import annotations

import re
from typing import Any


VALID_RECOMMENDATION_ACTIONS = ("Apply", "Review", "Skip")


def is_valid_analysis(analysis: Any) -> bool:
    """Return True when a parsed Gemini analysis has required usable fields."""
    if not isinstance(analysis, dict):
        return False

    score = analysis.get("score")
    recommendation = analysis.get("recommendation")

    if not isinstance(score, str) or score.strip() in ("", "N/A"):
        return False
    if not isinstance(recommendation, str) or recommendation.strip() in ("", "N/A"):
        return False

    recommendation_text = recommendation.strip()
    if "|" in recommendation_text:
        return False

    recommendation_action = re.match(r"^(Apply|Review|Skip)\b", recommendation_text, re.IGNORECASE)
    return recommendation_action is not None
