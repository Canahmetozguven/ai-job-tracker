# AI Job Tracker

Automated job scraper + AI analyzer that evaluates job fit and sends results to Telegram.

**Workflow:** Scrape jobs (JobSpy/LinkedIn) → AI analysis → Telegram alerts

---

## Quick Start

Requires [uv](https://docs.astral.sh/uv/) and uses Python 3.12 (installed automatically by uv when needed).

```bash
# 1. Install with your preferred analysis backend
uv sync --extra api       # API backend (pydantic-ai) — recommended
# OR
uv sync --extra browser   # Browser backend (Playwright)

# 2. Configure environment
cp .env.example .env  # Add your credentials (see Setup for backend-specific keys)

# 3. Add your CV
cp profile.example.txt profile.txt  # then edit it with your own CV

# 4. Scrape jobs
uv run job scrape --query "data scientist" --location "Turkey" --hours 1

# 5. Analyze with AI
uv run job analyze --jobs jobs.jsonl --hours 1

# 6. Or run everything automatically (cron/scheduler)
uv run job daily
```

---

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Scraper   │────▶│  jobs.jsonl │────▶│  Analyzer   │
│ JobSpy/LI   │     └─────────────┘     │ API / Browser│
└─────────────┘                          └──────┬──────┘
                                                │
                                          ┌─────▼─────┐
                                          │  Telegram │
                                          │   Bot     │
                                          └───────────┘
```

**Components:**

| File | Purpose |
|------|---------|
| `src/ai_job_tracker/cli.py` | The `job` Typer app — every command and flag |
| `src/ai_job_tracker/scraper.py` | Scrapes jobs from JobSpy/LinkedIn, outputs JSONL |
| `src/ai_job_tracker/analyzer.py` | Scores jobs against your profile with an LLM |
| `src/ai_job_tracker/llm.py` | Backend dispatch + API backend (pydantic-ai) |
| `src/ai_job_tracker/gemini_client.py` | Browser backend (Playwright → Gemini web UI) |
| `src/ai_job_tracker/run_daily.py` | Combines scraper + analyzer for scheduled runs |
| `src/ai_job_tracker/telegram_notify.py` | Sends formatted alerts to Telegram |
| `src/ai_job_tracker/config.py` | Settings model (`pydantic-settings`) + Big Tech matching |
| `src/ai_job_tracker/validate_proxies.py` | Tests proxies in parallel, saves working ones |
| `profile.example.txt` | Template CV — copy to `profile.txt` (gitignored) |

---

## Features

### Job Scraping
- **Multiple sources**: JobSpy (Indeed, LinkedIn, ZipRecruiter, Google) + LinkedIn-scraper
- **Proxy rotation**: Automatic proxy selection from validated pool
- **Freshness filter**: Only fetch jobs posted within last N hours
- **Daemon mode**: Continuous scraping at configurable intervals
- **Deduplication**: Avoids duplicate job entries

### AI Analysis
- **Two backends**: API (pydantic-ai, structured output, sub-second) or Browser (Playwright → Gemini web UI, no API key)
- **Provider-agnostic API**: Uses [pydantic-ai](https://ai.pydantic.dev/) — swap models by changing one env var
- **CV matching**: Compares job requirements against your profile
- **Fit scoring**: 1-10 scale with recommendation (Apply/Review/Skip)
- **Retry mechanism**: 3 retries (5s delay for API, 30s for browser)

### Proxy Validation
- **Parallel testing**: Tests 20 proxies concurrently
- **Smart early exit**: Stops after collecting 50+ working proxies
- **Performance sorting**: Fastest proxies first for optimal scraping
- **Automatic refresh**: Fresh proxy list validated on each run

### Automatic Proxy Scraping
- **Multi-source**: ProxyScrape, Free Proxy List, GeoNode in chain
- **Deduplication**: Removes duplicates across sources
- **Incremental**: Appends to existing proxy list (preserves working pool)
- **Graceful degradation**: Continues if one source fails

### Run Monitoring
- **Comprehensive summaries**: Tracks proxy validation, scraping, and analysis stats
- **Telegram reports**: Run summaries sent to Telegram after each cycle
- **Error tracking**: Collects and reports all failures
- **Logging**: All activity logged to `cron.log`

---

## Setup

### 1. Dependencies

Install the base package plus the analysis backend you want:

```bash
# API backend (recommended) — structured output via pydantic-ai
uv sync --extra api

# Browser backend — Playwright automation against Gemini web UI
uv sync --extra browser
uv run playwright install chromium   # download the browser binary
```

To run the test suite:

```bash
uv run pytest
```

### 2. Environment Variables

Copy the example and fill in your credentials:

```bash
cp .env.example .env
```

**For the API backend** (default):

```bash
ANALYSIS_BACKEND=api
AI_API_KEY=your-api-key-here
TELEGRAM_BOT_TOKEN=your-bot-token-here
TELEGRAM_CHAT_ID=your-chat-id-here
```

For Gemini (default model), get a free API key at [Google AI Studio](https://aistudio.google.com/api-keys).

**For the browser backend:**

```bash
ANALYSIS_BACKEND=browser
BROWSER_PROFILE_PATH=path/to/your/Brave/User Data
TELEGRAM_BOT_TOKEN=your-bot-token-here
TELEGRAM_CHAT_ID=your-chat-id-here
```

The browser profile must have an authenticated Gemini session.

Get a Telegram bot token from [@BotFather](https://t.me/BotFather). See
[Configuration](#configuration) for every supported key and its default.

### 3. Telegram Chat ID

Message [@userinfobot](https://t.me/userinfobot) to get your chat ID.

Set `TELEGRAM_CHAT_ID` in `.env` as shown above, or pass `--chat-id` to
`job analyze`. The application intentionally has no default destination.

### 4. Your CV

Copy `profile.example.txt` to `profile.txt` and replace it with your CV as plain text. The
file is gitignored, and its contents are inserted into every analysis prompt.

### 5. Proxy List

Place your proxy list in `proxies/proxyscrape_raw.txt` (one `host:port` per line). The `src/ai_job_tracker/run_daily.py` script automatically validates proxies and selects a working one for each scraping cycle.

---

## Usage

Everything runs through one command. `job --help` lists the subcommands, and
`job <command> --help` documents its flags:

| Command | Purpose |
|---------|---------|
| `job scrape` | Scrape jobs from JobSpy/LinkedIn |
| `job analyze` | Score jobs with AI and notify Telegram |
| `job daily` | Full pipeline: proxies, three scrape passes, analysis |
| `job career` | Scrape the Big Tech 7 career sites directly |
| `job proxies` | Fetch free proxies from public sources |
| `job validate-proxies` | Test a proxy list, keep the working ones |

Shell completion is available via `job --install-completion`.

### Scraper

```bash
# Interactive mode (prompts for every option)
uv run job scrape --interactive

# Command-line mode
uv run job scrape --query "data scientist" --location "Turkey" --limit 20

# Scrape only recent jobs (last 3 hours)
uv run job scrape --query "data scientist" --location "Turkey" --hours 3

# Daemon mode (continuous scraping)
uv run job scrape --query "data scientist" --location "Turkey" --daemon --interval 30

# Multiple sources with fallback
uv run job scrape --source 3  # JobSpy → LinkedIn fallback

# Big Tech 7 pass (global, company-filtered)
uv run job scrape --query "data scientist" --country worldwide --big-tech --hours 1
```

`--interactive` prompts for every option. Without it, `job scrape` prompts only
for `--query` and `--location` if they are missing (and skips the location
prompt under `--big-tech`, which searches globally); everything else falls back
to its documented default.

| Option | Default | Description |
|--------|---------|-------------|
| `--query`, `-q` | (prompted if omitted) | Job search query |
| `--location`, `-l` | (prompted if omitted) | Location (city, country); skipped under `--big-tech` |
| `--country` | `turkey` | Country for JobSpy's `country_indeed` (e.g. `turkey`, `worldwide`, `usa`, `uk`) |
| `--big-tech` | off | Post-filter results to Big Tech 7 (Apple, Microsoft, Google, Amazon, Meta, Nvidia, Tesla). Forces a global search; ignores `--location`. |
| `--source`, `-s` | `1` | 1=JobSpy, 2=LinkedIn, 3=Both with fallback |
| `--limit`, `-n` | `10` | Max results per source |
| `--output`, `-o` | `jobs.jsonl` | Output file |
| `--hours`, `-H` | `0` | Filter by age (hours), 0=disabled |
| `--daemon`, `-d` | false | Run continuously |
| `--interval`, `-i` | `30` | Minutes between scrapes (daemon mode) |
| `--proxy` | random from pool | Specific proxy to use |
| `--no-proxy` | off | Disable proxy rotation |
| `--append`, `-a` | off | Append to the output file instead of overwriting |
| `--interactive`, `-I` | off | Prompt for every option instead of reading flags |

### Analyzer

```bash
# Analyze all jobs in file
uv run job analyze --jobs jobs.jsonl

# Analyze only recent jobs (last 3 hours)
uv run job analyze --jobs jobs.jsonl --hours 3

# Skip already-analyzed jobs
uv run job analyze --jobs jobs.jsonl --skip-seen

# Limit to 5 jobs
uv run job analyze --jobs jobs.jsonl --limit 5
```

| Option | Default | Description |
|--------|---------|-------------|
| `--jobs` | `jobs.jsonl` | Job listings file |
| `--profile` | `profile.txt` | CV/profile file |
| `--limit` | `0` (all) | Max jobs to process |
| `--hours` | `0` | Only analyze jobs from last N hours |
| `--skip-seen` | false | Skip already-analyzed jobs |
| `--chat-id` | `TELEGRAM_CHAT_ID` | Telegram chat ID (required) |
| `--retries` | `3` | Max retries per job on LLM failure |

### Daily Runner

Combines scraper + analyzer in sequence with proxy validation and retry support:

```bash
# Single run
uv run job daily

# Override the destination for this run
uv run job daily --chat-id "your-chat-id"

# For cron (runs every 30 minutes)
*/30 * * * * cd /path/to/ai-job-tracker && .venv/bin/job daily >> cron.log 2>&1
```

The daily runner:
1. **Validates proxies** - Tests `proxies/proxyscrape_raw.txt` and saves working ones
2. **Pass 1 (Turkey local)** - Scrapes "data scientist" with `country=turkey` and `location=Turkey` into `jobs_linkedin.jsonl`
3. **Pass 2 (Big Tech 7)** - Scrapes "data scientist" globally and post-filters to Apple, Microsoft, Google, Amazon, Meta, Nvidia, Tesla — appends to the same JSONL
4. **Analyzes** - Sends each new job to the LLM for scoring
5. **Reports** - Prints summary + sends to Telegram (per-pass counts visible)

### Proxy Scraper

Standalone tool to fetch fresh proxies from online sources:

```bash
# Scrape all sources
uv run job proxies

# Scrape specific source only
uv run job proxies --source 1   # ProxyScrape
uv run job proxies --source 2   # Free Proxy List
uv run job proxies --source 3   # GeoNode
```

Proxies are appended to `proxies/proxyscrape_raw.txt`. `src/ai_job_tracker/run_daily.py` automatically calls this before validation.

### Proxy Validator

Standalone tool to test and filter proxies:

```bash
uv run job validate-proxies proxies/proxyscrape_raw.txt proxies/working.txt
```

| Option | Default | Description |
|--------|---------|-------------|
| `input_file` | (required) | Raw proxy list |
| `output_file` | (required) | Working proxies output |
| `MAX_WORKERS` | `20` | Parallel test threads |
| `MIN_WORKING` | `51` | Stop after this many working |
| `TIMEOUT` | `8` | Seconds per proxy test |

---

## Job File Format

Input/output uses JSONL (one JSON object per line):

```json
{"title": "Data Scientist", "company": "Acme", "location": "Remote", "job_url": "https://...", "description": "..."}
```

Analysis results are appended to `analysis_results.jsonl`:

```json
{"job": {"title": "...", "company": "...", ...}, "analysis": {"score": "8/10", "why_good": "...", "why_bad": "...", "recommendation": "Apply"}}
```

---

## Analysis Output

The analyzer sends each job to the configured LLM with your profile and returns structured output:

| Field | Example |
|-------|---------|
| `score` | `8/10` |
| `why_good` | Strong Python/SQL match, remote role |
| `why_bad` | Requires 5+ years, no visa sponsorship mentioned |
| `recommendation` | `Apply — tailor resume to Django and AWS` |

Score thresholds for Telegram notifications:
- **6-10**: Telegram alert sent
- **1-5**: Skipped (no notification, still saved to results file)

---

## Telegram Notifications

### Job Alerts
Individual job analysis results sent as jobs are analyzed:
```
📋 Job Analysis

🏢 Data Scientist at Acme
📍 Remote
🔗 https://...

⭐ Fit Score: 8/10

✅ Why Good:
...

❌ Why Bad:
...

📌 Recommendation: Apply
```

### Run Summary
After each `src/ai_job_tracker/run_daily.py` cycle, a summary report:
```
📊 Daily Job Scraper - Run Summary

✅ Proxy Validation
   Working: 51/238
   Selected: `178.212.144.7:80`

✅ Scraping
   Found: 12
   New: 12

✅ Analysis
   Processed: 12
   Succeeded: 10
   Failed: 2

✅ SUCCESS
```

---

## Troubleshooting

**Scraper returns 0 jobs**
- Check proxy list: `proxies/working.txt`
- LinkedIn may require session.json for authentication
- Try with `--no-proxy` to test direct connection

**Analyzer fails with "AI_API_KEY is required"**
- Set `AI_API_KEY` in `.env` with your provider's API key
- For Gemini: get a free key at https://aistudio.google.com/api-keys

**Browser backend: "No response received"**
- Verify Gemini is accessible: https://gemini.google.com/app
- Check the browser profile is logged into Gemini
- Set `BROWSER_PROFILE_PATH` in `.env`
- Run `uv run playwright install chromium` if not yet installed

**Telegram not sending**
- Verify bot token is correct in `.env`
- Ensure chat ID is correct
- Bot must have permission to message your chat

**Proxy validation fails**
- Check `proxies/proxyscrape_raw.txt` exists
- Verify internet connection
- Proxies may be blocked by the test URL

---

## Project Structure

```
.
├── pyproject.toml        # Project metadata, dependencies, console scripts
├── uv.lock               # Reproducible dependency lockfile
├── profile.example.txt   # CV template (copy to gitignored profile.txt)
├── src/ai_job_tracker/
│   ├── cli.py                # `job` Typer app — all argument parsing
│   ├── analyzer.py           # Job analyzer — scores jobs against a profile
│   ├── config.py             # Settings model (env / .env) + prompt template
│   ├── llm.py                # Backend dispatch + API backend (pydantic-ai)
│   ├── gemini_client.py      # Browser backend (Playwright → Gemini web UI)
│   ├── job_loader.py         # JSONL loader
│   ├── run_daily.py          # Scheduler (scraper + analyzer)
│   ├── scraper.py            # Job scraper (JobSpy/LinkedIn)
│   ├── career_scraper.py     # Big Tech career-site scraper CLI
│   ├── telegram_notify.py    # Telegram notifications
│   ├── proxy_scraper.py      # Auto-fetch proxies from online sources
│   ├── user_profile.py       # CV loader
│   ├── validate_proxies.py   # Proxy validator
│   └── career_scrapers/      # Per-company scrapers (add one file to extend)
│       ├── base.py           # BaseCareerScraper
│       └── amazon.py, google.py, meta.py, microsoft.py, apple.py, ...
├── scripts/
│   └── check_secrets.py  # Repo credential scanner (pre-commit + CI)
├── tests/
├── jobs.jsonl            # Scraped jobs (generated)
├── analysis_results.jsonl # Analysis output (generated)
├── cron.log              # Run logs (generated)
├── proxies/
│   ├── proxyscrape_raw.txt # Raw proxy list (provide your own)
│   └── working.txt         # Validated working proxies
└── docs/                 # Specs and plans
```

---

## Cron Setup

For automatic hourly scraping + analysis:

```bash
# Edit crontab
crontab -e

# Add this line (runs every 30 minutes)
*/30 * * * * cd /path/to/ai-job-tracker && .venv/bin/job daily >> cron.log 2>&1
```

Logs are written to `cron.log` in the project directory.

---

## Configuration

All settings come from the environment or a `.env` file — nothing is
hard-coded per machine. `.env.example` documents the full surface; copy it and
fill in what you need. A blank value is treated as unset, so the default applies.

| Env var | Description | Default |
|---------|-------------|---------|
| `ANALYSIS_BACKEND` | `api` or `browser` | `api` |
| `AI_API_KEY` | API key for the configured LLM provider (API backend) | *(required for api)* |
| `AI_MODEL` | [pydantic-ai model string](https://ai.pydantic.dev/models/) (API backend) | `google:gemini-2.5-flash` |
| `BROWSER_PROFILE_PATH` | Chrome/Brave profile with authenticated Gemini session (browser backend) | *(required for browser)* |
| `GEMINI_BROWSER_EXECUTABLE` | Browser executable path or command (browser backend) | *(Playwright's bundled Chromium)* |
| `GEMINI_URL` | Gemini web app URL (browser backend) | `https://gemini.google.com/app` |
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token | *(required to notify)* |
| `TELEGRAM_CHAT_ID` | Destination chat or channel ID | *(required to notify)* |
| `PROFILE_FILE` | Path to your CV text file | `profile.txt` |
| `JOBS_INPUT_FILE` | Default jobs file | `jobs.jsonl` |
| `ANALYSIS_OUTPUT_FILE` | Analysis results file | `analysis_results.jsonl` |

Precedence is process environment > `.env` > default. The settings model lives
in `src/ai_job_tracker/config.py` as a `pydantic-settings` `Settings` class;
field names map to the upper-case keys above.

To use a different LLM provider, install its extra and set `AI_MODEL` + `AI_API_KEY`:

```bash
# OpenAI (requires: uv pip install "pydantic-ai-slim[openai]")
AI_MODEL=openai:gpt-4o
AI_API_KEY=sk-...

# Anthropic (requires: uv pip install "pydantic-ai-slim[anthropic]")
AI_MODEL=anthropic:claude-sonnet-4-20250514
AI_API_KEY=sk-ant-...

# Google Gemini (default — included out of the box)
AI_MODEL=google:gemini-2.5-flash
AI_API_KEY=your-gemini-key
```

The prompt template is deliberately *not* a setting. It stays a constant
in `config.py`, and the selected profile file's contents are inserted at runtime.
