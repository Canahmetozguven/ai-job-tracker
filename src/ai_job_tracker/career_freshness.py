"""Date parsing and freshness policy for career-site job records."""

from __future__ import annotations

import datetime


ENGLISH_MONTH_NUMBERS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


def _parse_calendar_date(date_text: str) -> datetime.date | None:
    try:
        return datetime.date.fromisoformat(date_text)
    except ValueError:
        pass

    date_parts = date_text.replace(",", "").split()
    if len(date_parts) != 3:
        return None

    month_text, day_text, year_text = date_parts
    month_number = ENGLISH_MONTH_NUMBERS.get(month_text.lower())
    if month_number is None or not day_text.isdigit() or not year_text.isdigit():
        return None

    try:
        return datetime.date(int(year_text), month_number, int(day_text))
    except ValueError:
        return None


def _parse_latest_posted_at(date_posted: object) -> datetime.datetime | None:
    """Return the latest instant represented by a supported posting date."""
    if not isinstance(date_posted, str):
        return None

    normalized_date = date_posted.strip()
    if not normalized_date or normalized_date.lower() in {"unknown", "none", "null"}:
        return None

    calendar_date = _parse_calendar_date(normalized_date)
    if calendar_date is not None:
        return datetime.datetime.combine(calendar_date, datetime.time.max, tzinfo=datetime.UTC)

    try:
        posted_at = datetime.datetime.fromisoformat(normalized_date.replace("Z", "+00:00"))
    except ValueError:
        return None

    if posted_at.tzinfo is None:
        return posted_at.replace(tzinfo=datetime.UTC)
    return posted_at.astimezone(datetime.UTC)


def filter_recent_jobs(
    jobs: list[dict],
    hours: int,
    *,
    current_time: datetime.datetime | None = None,
) -> list[dict]:
    """Keep recent jobs, treating date-only values as whole-day intervals.

    ISO 8601 and Amazon's English ``Mon D, YYYY`` values are supported. Naive
    timestamps are interpreted as UTC and the cutoff is inclusive. A calendar
    date is retained when any instant in that day overlaps the requested
    window. Missing or malformed dates are retained because most registered
    sources cannot provide dates.
    """
    if hours <= 0:
        return jobs

    reference_time = current_time or datetime.datetime.now(datetime.UTC)
    if reference_time.tzinfo is None:
        reference_time = reference_time.replace(tzinfo=datetime.UTC)
    else:
        reference_time = reference_time.astimezone(datetime.UTC)
    cutoff_time = reference_time - datetime.timedelta(hours=hours)

    return [
        job
        for job in jobs
        if (posted_at := _parse_latest_posted_at(job.get("date_posted"))) is None
        or posted_at >= cutoff_time
    ]
