"""Big Tech career sites scraper CLI.

Loads every registered scraper from career_scrapers.SCRAPERS, invokes each
in isolation (per-scraper failure does not abort), aggregates the results,
dedupes by job_url, and writes to the output file with --append semantics.

Exit codes:
  0 — at least one scraper returned >0 jobs (others may have failed).
  1 — every scraper either raised an exception or returned 0 records.
"""

from __future__ import annotations

import argparse
import os
import sys

from career_scrapers import SCRAPERS, BaseCareerScraper
from scraper import append_jobs_jsonl, deduplicate_jobs, read_existing_jobs


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Big Tech 7 career-site scraper (Apple, Microsoft, Google, Amazon, Meta, Nvidia, Tesla)"
    )
    p.add_argument("--query", required=True, help="Job search query")
    p.add_argument("--limit", "-n", type=int, default=50, help="Max results per scraper")
    p.add_argument("--hours", "-H", type=int, default=0,
                   help="Filter by age (hours), 0=disabled. Currently a no-op for career sites; reserved for future use.")
    p.add_argument("--output", "-o", default="jobs_career.jsonl", help="Output file path")
    p.add_argument("--append", "-a", action="store_true", help="Append to output file (don't overwrite)")
    p.add_argument("--no-proxy", action="store_true", help="Disable proxy rotation")
    p.add_argument("--proxy", help="Use a specific proxy instead of random")
    return p


def _print_per_scraper_summary(results: dict, errors: dict) -> None:
    print("\nPer-scraper results:")
    for name in SCRAPERS:
        if name in errors:
            print(f"  ❌ {name}: {errors[name]}")
        else:
            count = len(results.get(name, []))
            print(f"  ✅ {name}: {count} job(s)")


def main(argv: list[str] | None = None) -> int:
    args = _build_argparser().parse_args(argv)
    sys.exit(_run(args))


def _run(args: argparse.Namespace) -> int:
    output: str = args.output
    proxy: str | None = None if args.no_proxy else args.proxy

    existing_urls: set[str] = set()
    if args.append and os.path.exists(output):
        existing_urls = read_existing_jobs(output)
        print(f"Loaded {len(existing_urls)} existing job URLs from {output}")

    results: dict[str, list[dict]] = {}
    errors: dict[str, str] = {}

    for name, scraper_cls in SCRAPERS.items():
        try:
            scraper: BaseCareerScraper = scraper_cls(proxy=proxy)
            records = scraper.fetch_jobs(args.query, limit=args.limit)
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
        if errors and len(errors) == len(SCRAPERS):
            print("\nAll scrapers failed. Exiting 1.")
            return 1
        print("\nNo records to write. Exiting 0.")
        return 0

    new_count = append_jobs_jsonl(all_records, output, existing_urls)
    print(f"\nWrote {new_count} new job(s) to {output}")
    return 0


if __name__ == "__main__":
    main()
