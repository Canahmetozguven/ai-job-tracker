# Big Tech Career Sites Scraper Design

## Overview

Add a third cron pass that scrapes each Big Tech 7 company's own career site (Apple, Microsoft, Google, Amazon, Meta, Nvidia, Tesla) directly, in addition to the existing LinkedIn/Indeed aggregator pass. Career sites have fresher data and the company-name is authoritative, but the implementation is per-company because each has its own (often reverse-engineered) search endpoint.

## Why

The current Big Tech 7 cron pass uses JobSpy + `--big-tech` post-filter. That only catches what LinkedIn/Indeed/Google Jobs aggregators have indexed, filtered to company names matching our `BIG_TECH_COMPANIES` list. With `--hours 1` the cron is finding 0-1 Big Tech jobs per run because:

1. Aggregators throttle and geo-restrict by proxy (we use international proxies).
2. Aggregator indexing lags the company's own posting by hours-to-days.
3. Some companies (Apple, Meta) post to their own careers portal first and syndicate to LinkedIn only when the role is "high-priority public."

Career sites eliminate the aggregator bottleneck. The trade-off is per-company integration work.

## Architecture

```
run_daily.py
   ├── Pass 1: scraper.py --country turkey           →  source_pass="turkey_local"
   ├── Pass 2: scraper.py --country worldwide --big-tech
   │                                                →  source_pass="big_tech_global"
   └── Pass 3: career_scraper.py                     →  source_pass="career_site"
            └── career_scrapers/ (registry of 7 scrapers)
                  ├── AmazonScraper
                  ├── GoogleScraper
                  ├── MetaScraper
                  ├── MicrosoftScraper
                  ├── AppleScraper
                  ├── NvidiaScraper  (Workday)
                  └── TeslaScraper
```

`career_scraper.py` is a new top-level CLI. It loads every registered scraper from `career_scrapers.SCRAPERS`, invokes each with the same query, aggregates the results, deduplicates, and writes to `jobs_linkedin.jsonl` with `--append`.

## File changes

### `career_scrapers/` (new package)

- `__init__.py` — `SCRAPERS: dict[str, type[BaseCareerScraper]]` registry. Importing every module here registers the scraper.
- `base.py` — `BaseCareerScraper` abstract class.
- `amazon.py` — `AmazonScraper`. Uses `https://amazon.jobs/en/search.json?` (confirmed working).
- `google.py` — `GoogleScraper`. Uses `https://careers.google.com/api/v3/search/` (needs research; my probe returned 404 — may need different headers/cookies, or a different endpoint like `/api/jobs/search`).
- `meta.py` — `MetaScraper`. Uses `https://www.metacareers.com/api/...` (needs research; my probe of three likely endpoints all 404).
- `microsoft.py` — `MicrosoftScraper`. Uses `https://careers.microsoft.com/api/...` (needs research).
- `apple.py` — `AppleScraper`. Uses `https://jobs.apple.com/api/...` (no public JSON API confirmed; may need to scrape search page).
- `nvidia.py` — `NvidiaScraper`. Uses `https://nvidia.wd5.myworkdayjobs.com/...` (Workday; known to require multi-step auth tokens).
- `tesla.py` — `TeslaScraper`. Uses `https://www.tesla.com/careers/...` (no public JSON API confirmed; may need to scrape search page).
- `tests/test_career_scrapers.py` — unit tests for `BaseCareerScraper` and one happy-path test per concrete scraper with mocked HTTP.

### `career_scraper.py` (new top-level CLI)

```
career_scraper.py --query QUERY [--hours N] [--limit N] [--proxy PROXY] [--output FILE] [--append]
```

Flow:
1. Load `SCRAPERS` registry.
2. For each scraper, in order: instantiate with proxy, call `fetch_jobs(query, limit)`, collect results. Per-scraper failure is caught, logged, and skipped — does not abort the run.
3. Deduplicate the combined result list by `job_url` (reuse `scraper.deduplicate_jobs`).
4. Write to output file with `--append` semantics (reuse `scraper.append_jobs_jsonl`).
5. Print per-scraper summary: name, jobs returned, status (ok/failed).
6. Exit 0 if at least one scraper returned >0 jobs; exit 1 if every scraper either raised an exception or returned 0 records.

### `career_scrapers/base.py` — `BaseCareerScraper`

```python
class BaseCareerScraper:
    name: ClassVar[str]                              # canonical ("Amazon")
    base_url: ClassVar[str]                          # "https://amazon.jobs"
    rate_limit_seconds: ClassVar[float] = 1.0
    max_retries: ClassVar[int] = 3

    def __init__(self, proxy: str | None = None):
        self.proxy = proxy
        self._last_request_at: float = 0.0

    def fetch_jobs(self, query: str, limit: int = 50) -> list[dict]:
        """Override in subclass. Return records matching the common schema."""
        raise NotImplementedError

    def _throttle(self) -> None: ...
    def _get(self, url: str, **kwargs) -> bytes:
        """GET with throttling, retry, optional proxy."""
        ...
    def _make_record(
        self, *, title, company, location, job_url,
        description=None, date_posted=None, source=None,
        is_remote=None, salary=None,
    ) -> dict:
        """Build a record dict with source_pass and source_company pre-filled."""
        return {
            "title": title, "company": company, "location": location,
            "job_url": job_url, "description": description,
            "date_posted": date_posted or "unknown", "job_type": None,
            "salary": salary, "source": source or self._source_tag(),
            "is_remote": is_remote,
            "source_pass": "career_site", "source_company": self.name,
        }
    def _source_tag(self) -> str:
        return f"{self.name.lower()}_career"
```

### Record schema

Same as existing JobSpy records, plus two new fields:

| Field            | Type   | Source                                            |
|------------------|--------|---------------------------------------------------|
| `source_pass`    | str    | `"career_site"` (NEW value; was `"turkey_local"` or `"big_tech_global"`) |
| `source_company` | str    | Canonical company name (e.g., `"Amazon"`)         |

All other fields are identical to JobSpy records so the analyzer, Telegram summary, and dedup logic work unchanged.

### `run_daily.py`

Add a 3rd invocation after the Big Tech 7 pass. Extend `run_summary["scrape"]` to:

```python
"scrape": {
    "turkey_local":    {"found": 0, "new": 0, "status": "not_run"},
    "big_tech_global": {"found": 0, "new": 0, "status": "not_run"},
    "career_site":     {"found": 0, "new": 0, "status": "not_run"},
},
```

New pass:
```python
print("  -> Pass 3: Big Tech career sites")
scrape_ok_c = run_command([
    PYTHON, "career_scraper.py",
    "--query", "data scientist",
    "--hours", "168",                # 7 days — career sites update less often
    "--output", "jobs_linkedin.jsonl",
    "--proxy", proxy,
    "--append",
], "Scraping Big Tech career sites")
_update_pass_summary("career_site", scrape_ok_c)
```

Failure-exit: `if not (scrape_ok_a or scrape_ok_b or scrape_ok_c):` (analyzer runs if any pass succeeded; exit 1 only if all three failed).

### `telegram_notify.py`

Extend `format_run_summary` to render a third row in the Scraping section:
```python
pass_labels = {
    "turkey_local":    "🇹🇷 Turkey local",
    "big_tech_global": "🌍 Big Tech 7",
    "career_site":     "🏢 Career sites",
}
```

Per-pass `any(...)` check for the overall status: continue to use the existing pattern.

### `tests/test_analyzer.py`

Add tests for the new 3-pass `format_run_summary` shape, mirroring the existing per-pass tests.

## Behavior

- A job that appears on both LinkedIn (in `big_tech_global`) and the company's career site (in `career_site`) is **kept twice** in the JSONL — different `job_url`, different `description`, different `source`. The analyzer will score both, and Telegram will receive both. (Per the brainstorming decision: keep both, accept duplicate analyses as a known tradeoff.)
- A career site record with the **same** `job_url` as a JobSpy record (e.g., a LinkedIn deep link that points to the company site) is deduped by the existing `deduplicate_jobs` logic.
- A scraper that fails (HTTP 403, parse error, network timeout) contributes 0 records, logs its error, and the run continues with the other scrapers.
- The career site pass uses `--hours 168` (7 days) instead of `--hours 1` because career-site postings change less frequently and we don't want to miss a posting that the aggregator would have caught only after a few days.

## Error handling

| Condition                                       | Behavior                                                                                       |
|-------------------------------------------------|------------------------------------------------------------------------------------------------|
| Single scraper raises exception                 | Log `{scraper.name}: {error}`, skip. Other scrapers continue.                                  |
| All 7 scrapers raise exception                  | Exit 1, set `career_site` status `failed`, mark `analyze` as `skipped`.                        |
| Some scrapers return 0 jobs, others succeed     | Exit 0, set `career_site` status `success` (we got something).                                  |
| HTTP 429 (rate limited)                         | `BaseCareerScraper._get` retries with backoff. After 3 retries, raises. Caught at the CLI level. |
| HTTP 5xx                                        | Same as 429.                                                                                   |
| Network timeout / connection reset              | Same as 429.                                                                                   |
| Malformed JSON response                         | Scraper logs, returns `[]` for that scraper. Continues with others.                            |

## Testing

### Unit tests (`tests/test_career_scrapers.py`, new)

- `BaseCareerScraper.throttle()` — verifies time between calls respects `rate_limit_seconds`.
- `BaseCareerScraper._get()` — verifies retry on HTTP 5xx, gives up after `max_retries`.
- `BaseCareerScraper._make_record()` — verifies the output has all required fields including `source_pass="career_site"` and `source_company=self.name`.
- One happy-path test per concrete scraper with mocked HTTP response (fixture JSON in `tests/fixtures/career_sites/`).
- `SCRAPERS` registry contains all 7 expected companies.

### CLI tests (`tests/test_career_scraper_cli.py`, new)

- `career_scraper.py --help` shows the expected flags.
- Aggregated output combines records from multiple mocked scrapers.
- Deduplication: two scrapers returning the same `job_url` produce one record.
- Failure isolation: one scraper raising an exception does not prevent others from contributing.

### Integration smoke test (manual, documented in this spec)

```bash
.venv/bin/python career_scraper.py --query "data scientist" --hours 168 --limit 20 \
    --output /tmp/test_career.jsonl --append

# Verify per-company breakdown
jq -c 'select(.source_pass=="career_site")' /tmp/test_career.jsonl \
    | jq -r '.source_company' | sort | uniq -c
```

Expected: at least Amazon contributes non-zero records (confirmed API). Google, Meta, Microsoft may or may not contribute depending on endpoint discovery effort. Apple, Nvidia, Tesla may contribute zero (no confirmed public API; will be flagged as experimental).

### Live cron verification (after implementation)

- Trigger one full `run_daily.py` cycle.
- `cron.log` shows all three passes with the new `🏢 Career sites` row.
- `telegram_notify` summary includes the third row.
- Per-scraper pass/fail logged in the career-scraper CLI output.

## Backward compatibility

- Existing `source_pass` values (`turkey_local`, `big_tech_global`) unchanged. New value is additive.
- Existing dedup, analyzer, and summary code paths continue to work because career-site records match the existing record schema plus two extra fields (which all consumers ignore).
- `format_run_summary` rendering loop iterates the keys of `run_summary["scrape"]` — adding `"career_site"` to the dict automatically adds the third row.

## Out of scope

- Playwright/headless-browser fallback for Apple, Nvidia, Tesla if the HTTP scrapers fail. The HTTP scraper is a first attempt; we add Playwright only if it's clearly worth the maintenance.
- Auto-discovery of new Big Tech companies (the list is fixed at Apple/Microsoft/Google/Amazon/Meta/Nvidia/Tesla).
- De-duplication of career-site records against LinkedIn big_tech records by `(title, company)`. Different `job_url` = different record.
- Per-company proxy rotation (career sites are less rate-limit-sensitive than LinkedIn/Indeed).
- Persistent session cookies for Workday (Nvidia) — first scrape may be flaky; revisit if needed.
- Adding a "Big Tech career sites" sub-section in the Telegram message that shows per-company counts (would expand the message; not requested).
