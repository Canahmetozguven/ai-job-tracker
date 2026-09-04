"""Big Tech career sites scraper CLI.

Loads every registered scraper from career_scrapers.SCRAPERS, invokes each
in isolation (per-scraper failure does not abort), aggregates the results,
dedupes by job_url, and writes to the output file with --append semantics.

Exit codes:
  0 — at least one scraper returned >0 jobs (others may have failed).
  1 — every scraper either raised an exception or returned 0 records.
"""

from __future__ import annotations

import datetime
import os

from ai_job_tracker.career_scrapers import SCRAPERS, BaseCareerScraper
from ai_job_tracker.scraper import append_jobs_jsonl, deduplicate_jobs, read_existing_jobs


AMAZON_DATE_FORMAT = "%b %d, %Y"


def _parse_posted_at(date_posted: object) -> datetime.datetime | None:
    if not isinstance(date_posted, str):
        return None

    normalized_date = date_posted.strip()
    if not normalized_date or normalized_date.lower() in {"unknown", "none", "null"}:
        return None

    try:
        posted_at = datetime.datetime.fromisoformat(normalized_date.replace("Z", "+00:00"))
    except ValueError:
        try:
            posted_at = datetime.datetime.strptime(normalized_date, AMAZON_DATE_FORMAT)
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
    """Keep recent career jobs while retaining records with uncertain dates.

    ISO 8601 and Amazon's ``Mon D, YYYY`` values are supported. Naive values
    are interpreted as UTC and the cutoff is inclusive. Missing or malformed
    dates are retained because most registered sources cannot provide dates.
    """
    if hours <= 0:
        return jobs

    reference_time = current_time or datetime.datetime.now(datetime.UTC)
    if reference_time.tzinfo is None:
        reference_time = reference_time.replace(tzinfo=datetime.UTC)
    else:
        reference_time = reference_time.astimezone(datetime.UTC)
    cutoff_time = reference_time - datetime.timedelta(hours=hours)

    filtered_jobs = []
    for job in jobs:
        posted_at = _parse_posted_at(job.get("date_posted"))
        if posted_at is None or posted_at >= cutoff_time:
            filtered_jobs.append(job)
    return filtered_jobs


def _print_per_scraper_summary(results: dict, errors: dict) -> None:
    print("\nPer-scraper results:")
    for name in SCRAPERS:
        if name in errors:
            print(f"  ❌ {name}: {errors[name]}")
        else:
            count = len(results.get(name, []))
            print(f"  ✅ {name}: {count} job(s)")


def run(
    *,
    query: str,
    limit: int = 50,
    hours: int = 0,
    output: str = "jobs_career.jsonl",
    append: bool = False,
    no_proxy: bool = False,
    proxy: str | None = None,
) -> int:
    """Scrape every registered career site and write deduped results.

    Returns the process exit code: 0 if any scraper contributed records,
    1 if every scraper either raised or returned nothing.
    """
    proxy = None if no_proxy else proxy

    existing_urls: set[str] = set()
    if append and os.path.exists(output):
        existing_urls = read_existing_jobs(output)
        print(f"Loaded {len(existing_urls)} existing job URLs from {output}")

    results: dict[str, list[dict]] = {}
    errors: dict[str, str] = {}

    for name, scraper_cls in SCRAPERS.items():
        try:
            scraper: BaseCareerScraper = scraper_cls(proxy=proxy)
            records = scraper.fetch_jobs(query, limit=limit)
            results[name] = records
            print(f"  [{name}] fetched {len(records)} record(s)")
        except Exception as e:
            errors[name] = f"{type(e).__name__}: {e}"
            print(f"  [{name}] FAILED: {errors[name]}")

    _print_per_scraper_summary(results, errors)

    all_records: list[dict] = []
    for recs in results.values():
        all_records.extend(recs)
    all_records = deduplicate_jobs(all_records)

    if not all_records:
        # No records contributed by any scraper — either every scraper raised
        # an exception, or every scraper returned [] (or a mix of both).
        # Per spec, exit 1 in either case.
        n_errored = len(errors)
        n_total = len(SCRAPERS)
        n_empty = n_total - n_errored
        print(f"\nNo records from any scraper ({n_errored} errors, {n_empty} empty). Exiting 1.")
        return 1

    if hours > 0:
        unfiltered_count = len(all_records)
        all_records = filter_recent_jobs(all_records, hours)
        print(f"\nFreshness filter kept {len(all_records)} of {unfiltered_count} job(s) from the last {hours} hours")

    new_count = append_jobs_jsonl(all_records, output, existing_urls)
    print(f"\nWrote {new_count} new job(s) to {output}")
    return 0


if __name__ == "__main__":  # pragma: no cover - delegated to the `job` CLI
    from ai_job_tracker.cli import app

    app()
