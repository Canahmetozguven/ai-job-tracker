# Turkey-Local + Big Tech Job Sourcing Design

## Overview

Replace the cronjob's single JobSpy pass with two passes that merge into one
output file:

1. **Turkey-local pass** — `data scientist` jobs located in Turkey, any
   remote status, with country=Türkiye so Indeed and LinkedIn return
   Turkey-rooted results.
2. **Big Tech 7 pass** — `data scientist` jobs at Apple, Microsoft, Google,
   Amazon, Meta, Nvidia, or Tesla, searched globally and post-filtered by
   company name.

The cron previously produced a mix of unrelated international remote roles
(Jobgether, Crossing Hurdles, EPAM, Wiser AI, etc.) because (a) the recent
addition of `linkedin_fetch_description=True` causes LinkedIn to broaden its
result set, and (b) `country_indeed` was not set, so the default `Country.USA`
mixed with location "Turkey" returned US-rooted global roles. The two-pass
design fixes both.

## Architecture

```
run_daily.py
   │
   ├── Pass 1: scraper.py --country turkey
   │           (site=linkedin/indeed/google, NO zip_recruiter [403s],
   │            linkedin_fetch_description=True)
   │           → append to jobs_linkedin.jsonl  (source_pass="turkey_local")
   │
   ├── Pass 2: scraper.py --country worldwide --big-tech
   │           (no location filter, post-filter company in BIG_TECH_COMPANIES,
   │            site=linkedin/indeed/google)
   │           → append to jobs_linkedin.jsonl  (source_pass="big_tech_global")
   │           (dedup by job_url — duplicates with pass 1 are dropped)
   │
   └── analyzer.py on jobs_linkedin.jsonl → Telegram (single stream,
                                            each job has source_pass tag)
```

Both passes include on-site, hybrid, and remote jobs. No `is_remote` filter
is applied (would be a `False` default and meaningless as a filter).

## Big Tech 7 list

| Canonical | Aliases (case-insensitive substring match) |
|-----------|--------------------------------------------|
| Apple     | Apple, Apple Inc |
| Microsoft | Microsoft, Microsoft Corporation |
| Google    | Google, Alphabet, YouTube, Waymo, DeepMind, Google LLC |
| Amazon    | Amazon, Amazon Web Services, AWS |
| Meta      | Meta, Meta Platforms, Facebook |
| Nvidia    | Nvidia, NVIDIA, Nvidia Corporation |
| Tesla     | Tesla, Tesla Motors |

`config.py` gains:

```python
BIG_TECH_COMPANIES: dict[str, list[str]] = { ... }

def match_big_tech(company: str | None) -> str | None:
    """Return canonical company name if company matches an alias, else None."""
    if not company:
        return None
    company_lower = company.lower()
    for canonical, aliases in BIG_TECH_COMPANIES.items():
        if any(alias.lower() in company_lower for alias in aliases):
            return canonical
    return None
```

## File Changes

### `config.py`

- Add `BIG_TECH_COMPANIES` dict.
- Add `match_big_tech(company)` function.
- No other constants change.

### `scraper.py`

**New CLI flags:**
- `--country {turkey,worldwide,usa,uk,germany,...}` — maps to JobSpy's
  `country_indeed` parameter. Default: `turkey`.
- `--big-tech` — when set, post-filter records via `match_big_tech`. Default:
  off.
- When `--big-tech` is set, force `location=None` (search is global).

**Function changes:**
- `scrape_with_jobspy(query, location, limit, hours_old, proxy, country, source_pass)`
  gets two new kwargs. Builds JobSpy kwargs with `country_indeed=country`.
- `df_to_job_records(df, source_pass)` gets one new required arg. Each record
  gets `"source_pass": source_pass`.
- New `filter_big_tech(records) -> list[dict]` that drops non-matching records
  and adds `"big_tech_company": "<canonical>"` to each survivor.

**Site list change:**
- Remove `"zip_recruiter"` from `site_name` (consistently 403s in `cron.log`).
- New default: `["linkedin", "indeed", "google"]`.
- Keep `"linkedin_fetch_description": True` (analyzer needs full descriptions
  for good fit scoring).

**`main()` CLI flow:**
- Read `--country` (default `turkey`) and `--big-tech` (default off).
- If `--big-tech`, set `location=None` regardless of `--location` arg.
- Call `scrape_with_jobspy(...)` then `df_to_job_records(..., source_pass)`.
- If `--big-tech`, call `filter_big_tech(records)` before write.
- Existing `--append` / dedup flow unchanged.

### `run_daily.py`

Replace the single `scraper.py` invocation with two sequential calls. Each
uses `--append` so both write to `jobs_linkedin.jsonl`:

```python
# Pass 1: Turkey-located
run_command([
    PYTHON, "scraper.py",
    "--query", "data scientist",
    "--country", "turkey",
    "--hours", "1",
    "--output", "jobs_linkedin.jsonl",
    "--proxy", proxy,
    "--append",
], "Scraping Turkey-local jobs")

# Pass 2: Big Tech 7 (global)
run_command([
    PYTHON, "scraper.py",
    "--query", "data scientist",
    "--country", "worldwide",
    "--big-tech",
    "--hours", "1",
    "--output", "jobs_linkedin.jsonl",
    "--proxy", proxy,
    "--append",
], "Scraping Big Tech 7 jobs")
```

**Run summary tracking:** the existing `run_summary["scrape"]` block becomes a
per-pass breakdown:

```python
run_summary["scrape"] = {
    "turkey_local":   {"found": 0, "new": 0, "status": "not_run"},
    "big_tech_global": {"found": 0, "new": 0, "status": "not_run"},
}
```

The Telegram summary reports both buckets separately. Existing `format_run_summary`
in `telegram_notify.py` gets a small additive change to render two rows.

**Failure handling:** if pass 1 fails, **still run pass 2**. If pass 2 fails,
**still run analyzer** on whatever made it to JSONL. Only exit 1 if both passes
fail outright. If both passes succeed but the combined JSONL has no new records,
the analyzer is still invoked and no Telegram summary is sent (no new analysis
to report).

### `analyzer.py`

No changes. The analyzer reads `source_pass` from the job record (or treats it
as missing for legacy records) and flows it into `analysis_results.jsonl`.
Future filtering of Telegram notifications by `source_pass` is out of scope.

## Behavior

- Either pass can be disabled with a flag without breaking the other.
- A Big Tech job already in the Turkey pass is dropped from the Big Tech pass
  (dedup by `job_url` in `append_jobs_jsonl`).
- A Big Tech role that is also based in Turkey will appear with
  `source_pass="turkey_local"` (pass 1 wins on dedup).
- `--big-tech` combined with `--country turkey` is allowed — user can search
  Turkey-based Big Tech roles if they want. No special warning.

## Error handling

| Failure | Behavior |
|---------|----------|
| Pass 1 (Turkey) scrape fails | Log error, mark failed in summary, still run pass 2. |
| Pass 2 (Big Tech) scrape fails | Log error, mark failed in summary, still run analyzer. |
| Both passes fail | Exit 1 (no jobs to analyze). |
| Pass returns 0 jobs | Not an error — log "0 jobs" for that pass, continue. |
| `--big-tech` finds 0 matches | Log "N records dropped by big_tech filter" so the filter's effect is visible. |
| `match_big_tech(None)` or `""` | Returns `None` — company-less records are filtered out. No crash. |
| JSONL file missing at analysis time | Already handled (analyzer reads what's there, no-op on empty). |
| Per-site JobSpy failure (5xx, 403) | JobSpy already isolates failures per site; one bad site doesn't kill the rest. |

## Testing

### Unit tests (`tests/test_scraper.py` additions, new `tests/test_config.py`)

- `match_big_tech("Meta Platforms")` → `"Meta"`
- `match_big_tech("meta")` → `"Meta"` (case-insensitive)
- `match_big_tech("Facebook")` → `"Meta"` (alias)
- `match_big_tech("Acme Co")` → `None`
- `match_big_tech(None)` → `None`
- `match_big_tech("")` → `None`
- `match_big_tech("Tesla Motors Inc")` → `"Tesla"`
- `match_big_tech("Amazon Web Services")` → `"Amazon"`
- `df_to_job_records` includes `source_pass` field
- `filter_big_tech` drops non-matches and tags `big_tech_company` on survivors
- CLI: `--country` and `--big-tech` flags parse correctly
- CLI: `--country turkey` is the default

### Integration smoke test (manual, documented in this spec)

```bash
# Pass 1 only — Turkey local
.venv/bin/python scraper.py --query "data scientist" --country turkey \
    --hours 1 --limit 5 --no-proxy --output /tmp/test_turkey.jsonl --append

# Pass 2 only — Big Tech global
.venv/bin/python scraper.py --query "data scientist" --country worldwide \
    --big-tech --hours 1 --limit 20 --no-proxy --output /tmp/test_bigtech.jsonl --append

# Verify
jq -c 'select(.source_pass=="turkey_local")' /tmp/test_turkey.jsonl | wc -l
jq -c 'select(.source_pass=="big_tech_global")' /tmp/test_bigtech.jsonl | wc -l
jq -r 'select(.source_pass=="big_tech_global") | .big_tech_company' /tmp/test_bigtech.jsonl | sort -u
```

### Live cron verification (after implementation)

- Trigger one full `run_daily.py` cycle.
- `cron.log` shows both passes.
- `analysis_results.jsonl` contains records with both `source_pass` values.
- Telegram summary shows `turkey_local` and `big_tech_global` count buckets.
- No regression: existing single-pass `scraper.py` invocations from the README
  still work (defaults preserve current behavior).

## Backward compatibility

- Single-pass `scraper.py` invocations: unchanged default behavior
  (`--country turkey` + no `--big-tech` + `source_pass="turkey_local"`).
- Existing `jobs.jsonl` records without `source_pass` are still loadable
  by the analyzer.
- `run_daily.py` summary block is additively extended; the Telegram message
  format extends but doesn't break.

## Out of scope

- Filtering Telegram notifications by `source_pass` (the analyzer's output
  flows to Telegram as today; both buckets notify).
- Per-pass proxy rotation (both passes share the same proxy selection from
  the existing random pick).
- Other JobSpy sites (`glassdoor`, `bayt`, `naukri`, `bdjobs` are available
  but not enabled by this change).
- Changes to the analyzer's scoring prompt or thresholds.
