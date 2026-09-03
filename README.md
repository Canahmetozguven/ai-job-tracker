# AI Job Tracker

Automated job scraper + AI analyzer that evaluates job fit and sends results to Telegram.

**Workflow:** Scrape jobs (JobSpy/LinkedIn) → AI analysis (Gemini) → Telegram alerts

---

## Quick Start

Requires [uv](https://docs.astral.sh/uv/) and uses Python 3.12 (installed automatically by uv when needed).

```bash
# 1. Install dependencies
uv sync

# 2. Install the browser used by the Gemini integration
uv run playwright install chromium

# 3. Configure environment
cp .env.example .env  # Add your Telegram bot token and chat ID

# 4. Add your CV
cp profile.example.txt profile.txt  # then edit it with your own CV

# 5. Scrape jobs
uv run job scrape --query "data scientist" --location "Turkey" --hours 1

# 6. Analyze with AI
uv run job analyze --jobs jobs.jsonl --hours 1

# 7. Or run everything automatically (cron/scheduler)
uv run job daily
```

---

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Scraper   │────▶│  jobs.jsonl │────▶│  Analyzer   │
│ JobSpy/LI   │     └─────────────┘     │   Gemini    │
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
| `src/ai_job_tracker/analyzer.py` | Uses Gemini AI to evaluate job fit |
| `src/ai_job_tracker/run_daily.py` | Combines scraper + analyzer for scheduled runs |
| `src/ai_job_tracker/telegram_notify.py` | Sends formatted alerts to Telegram |
| `src/ai_job_tracker/gemini_client.py` | Browser automation for Gemini |
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
- **Gemini integration**: Browser automation for AI-powered job evaluation
- **CV matching**: Compares job requirements against your profile
- **Fit scoring**: 1-10 scale with recommendation (Apply/Review/Skip)
- **Retry mechanism**: 3 retries with 30s delay on failures

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

```bash
uv sync
uv run playwright install chromium
```

`uv sync` installs the runtime dependencies and the `dev` dependency group from `pyproject.toml`. To run the test suite:

```bash
uv run pytest
```

### 2. Environment Variables

Copy the example and fill in your credentials:

```bash
cp .env.example .env
```

At minimum, set:

```bash
TELEGRAM_BOT_TOKEN=your-bot-token-here
TELEGRAM_CHAT_ID=your-chat-id-here
```

Get a bot token from [@BotFather](https://t.me/BotFather) on Telegram. See
[Configuration](#configuration) for every supported key and its default.

### 3. Telegram Chat ID

Message [@userinfobot](https://t.me/userinfobot) to get your chat ID.

Set `TELEGRAM_CHAT_ID` in `.env` as shown above, or pass `--chat-id` to
`job analyze`. The application intentionally has no default destination.

### 4. Browser Profile (for Gemini)

The analyzer uses Brave browser with an existing profile that's logged into Gemini.

**Option A: Use existing Brave profile**
```bash
# .env
BROWSER_PROFILE_PATH=path/to/your/Brave/User Data
```

**Option B: Install Brave Nightly** (Linux)
```bash
# Download from https://brave.com/download-nightly/
# Or use the included installer if available
```

### 5. Your CV

Copy `profile.example.txt` to `profile.txt` and replace it with your CV as plain text. The
file is gitignored, and its contents are inserted into every Gemini prompt.

### 6. Proxy List

Place your proxy list in `proxies/proxyscrape_raw.txt` (one `host:port` per line). The `src/ai_job_tracker/run_daily.py` script automatically validates proxies and selects a working one for each scraping cycle.

---

## Usage

Everything runs through one command. `job --help` lists the subcommands, and
`job <command> --help` documents its flags:

| Command | Purpose |
|---------|---------|
| `job scrape` | Scrape jobs from JobSpy/LinkedIn |
| `job analyze` | Score jobs with Gemini and notify Telegram |
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
| `--retries` | `3` | Max retries per job on Gemini failure |

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
4. **Analyzes** - Sends each new job to Gemini AI for scoring
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

## Gemini Response Format

The analyzer sends each job to Gemini with your profile and expects:

```
1. FIT SCORE: X/10
2. WHY GOOD: ...
3. WHY BAD: ...
4. RECOMMENDATION: Apply/Skip/Review
```

Score meanings:
- **8-10**: Strong match - Telegram alert sent
- **5-7**: Review - Telegram alert sent
- **1-4**: Skip - Skipped (no notification)

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

**Analyzer "No response received"**
- Verify Gemini is accessible: https://gemini.google.com/app
- Check browser profile is logged in
- Try increasing wait time in `src/ai_job_tracker/gemini_client.py`

**Telegram not sending**
- Verify bot token is correct in `.env`
- Ensure chat ID is correct
- Bot must have permission to message your chat

**Browser won't launch**
- Set `BROWSER_PROFILE_PATH` (and optionally `GEMINI_BROWSER_EXECUTABLE`) in `.env`
- On Linux: `sudo apt install brave-browser`

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
│   ├── analyzer.py           # AI job analyzer (Gemini)
│   ├── config.py             # Settings model (env / .env) + prompt template
│   ├── gemini_client.py      # Browser automation for Gemini
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
fill in what you need. Every key is optional except the Telegram credentials,
and a blank value is treated as unset, so the default applies.

| Env var | Description | Default |
|---------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token | *(required to notify)* |
| `TELEGRAM_CHAT_ID` | Destination chat or channel ID | *(required to notify)* |
| `BROWSER_PROFILE_PATH` | Brave/Chrome profile with an authenticated Gemini session | `USER_INFO_BACKUP_DESKTOP-MR1KOEH/Brave/User Data` |
| `GEMINI_BROWSER_EXECUTABLE` | Browser executable or command for Gemini | *(Playwright's bundled Chromium)* |
| `GEMINI_URL` | Gemini web app URL | `https://gemini.google.com/app` |
| `PROFILE_FILE` | Path to your CV text file | `profile.txt` |
| `JOBS_INPUT_FILE` | Default jobs file | `jobs.jsonl` |
| `ANALYSIS_OUTPUT_FILE` | Analysis results file | `analysis_results.jsonl` |

Precedence is process environment > `.env` > default. The settings model lives
in `src/ai_job_tracker/config.py` as a `pydantic-settings` `Settings` class;
field names map to the upper-case keys above.

The Gemini prompt template is deliberately *not* a setting. It stays a constant
in `config.py`, and the selected profile file's contents are inserted at runtime.
