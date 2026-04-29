# AI Job Tracker

Automated job scraper + AI analyzer that evaluates job fit and sends results to Telegram.

**Workflow:** Scrape jobs (JobSpy/LinkedIn) → AI analysis (Gemini) → Telegram alerts

---

## Quick Start

```bash
# 1. Install dependencies
uv sync

# 2. Configure environment
cp .env.example .env  # Add your Telegram bot token

# 3. Add your CV
echo "Your CV text here..." > profile.txt

# 4. Scrape jobs
uv run python scraper.py --query "data scientist" --location "Turkey" --hours 1

# 5. Analyze with AI
uv run python analyzer.py --jobs jobs.jsonl --hours 1

# 6. Or run everything automatically (cron/scheduler)
uv run python run_daily.py
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
| `scraper.py` | Scrapes jobs from JobSpy/LinkedIn, outputs JSONL |
| `analyzer.py` | Uses Gemini AI to evaluate job fit |
| `run_daily.py` | Combines scraper + analyzer for scheduled runs |
| `telegram_notify.py` | Sends formatted alerts to Telegram |
| `gemini_client.py` | Browser automation for Gemini |
| `config.py` | Central configuration |
| `validate_proxies.py` | Tests proxies in parallel, saves working ones |
| `profile.txt` | Your CV as plain text |

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
# or: pip install python-jobspy linkedin-scraper playwright python-telegram-bot python-dotenv
```

### 2. Environment Variables

Create `.env` file:

```bash
TELEGRAM_BOT_TOKEN=your-bot-token-here
```

Get a bot token from [@BotFather](https://t.me/BotFather) on Telegram.

### 3. Telegram Chat ID

Message [@userinfobot](https://t.me/userinfobot) to get your chat ID.

Update `config.py`:
```python
DEFAULT_CHAT_ID = "your-chat-id"
```

### 4. Browser Profile (for Gemini)

The analyzer uses Brave browser with an existing profile that's logged into Gemini.

**Option A: Use existing Brave profile**
```python
# config.py
BROWSER_PROFILE_PATH = "path/to/your/Brave/User Data"
```

**Option B: Install Brave Nightly** (Linux)
```bash
# Download from https://brave.com/download-nightly/
# Or use the included installer if available
```

### 5. Your CV

Edit `profile.txt` with your CV as plain text. This is included in every Gemini prompt.

### 6. Proxy List

Place your proxy list in `proxies/proxyscrape_raw.txt` (one `host:port` per line). The `validate_proxies.py` script will test them and save working ones to `proxies/working.txt`.

---

## Usage

### Scraper

```bash
# Interactive mode (prompts for input)
uv run python scraper.py

# Command-line mode
uv run python scraper.py --query "data scientist" --location "Turkey" --limit 20

# Scrape only recent jobs (last 3 hours)
uv run python scraper.py --query "data scientist" --location "Turkey" --hours 3

# Daemon mode (continuous scraping)
uv run python scraper.py --query "data scientist" --location "Turkey" --daemon --interval 30

# Multiple sources with fallback
uv run python scraper.py --source 3  # JobSpy → LinkedIn fallback
```

| Option | Default | Description |
|--------|---------|-------------|
| `--query`, `-q` | (required) | Job search query |
| `--location`, `-l` | (required) | Location (city, country) |
| `--source`, `-s` | `1` | 1=JobSpy, 2=LinkedIn, 3=Both with fallback |
| `--limit`, `-n` | `10` | Max results per source |
| `--output`, `-o` | `jobs.jsonl` | Output file |
| `--hours`, `-H` | `0` | Filter by age (hours), 0=disabled |
| `--daemon`, `-d` | false | Run continuously |
| `--interval`, `-i` | `30` | Minutes between scrapes (daemon mode) |
| `--proxy` | random from pool | Specific proxy to use |

### Analyzer

```bash
# Analyze all jobs in file
uv run python analyzer.py --jobs jobs.jsonl

# Analyze only recent jobs (last 3 hours)
uv run python analyzer.py --jobs jobs.jsonl --hours 3

# Skip already-analyzed jobs
uv run python analyzer.py --jobs jobs.jsonl --skip-seen

# Limit to 5 jobs
uv run python analyzer.py --jobs jobs.jsonl --limit 5
```

| Option | Default | Description |
|--------|---------|-------------|
| `--jobs` | `jobs.jsonl` | Job listings file |
| `--profile` | `profile.txt` | CV/profile file |
| `--limit` | `0` (all) | Max jobs to process |
| `--hours` | `0` | Only analyze jobs from last N hours |
| `--skip-seen` | false | Skip already-analyzed jobs |
| `--chat-id` | from config | Telegram chat ID |
| `--retries` | `3` | Max retries per job on Gemini failure |

### Daily Runner

Combines scraper + analyzer in sequence with proxy validation and retry support:

```bash
# Single run
uv run python run_daily.py

# For cron (runs every 30 minutes)
*/30 * * * * cd /home/can/Desktop/job && /home/can/Desktop/job/.venv/bin/python run_daily.py >> cron.log 2>&1
```

The daily runner:
1. **Validates proxies** - Tests `proxies/proxyscrape_raw.txt` and saves working ones
2. **Scrapes jobs** - Uses a random working proxy for JobSpy/LinkedIn
3. **Analyzes jobs** - Sends each job to Gemini AI for scoring
4. **Reports results** - Prints summary + sends to Telegram

### Proxy Validator

Standalone tool to test and filter proxies:

```bash
python validate_proxies.py proxies/proxyscrape_raw.txt proxies/working.txt
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
After each `run_daily.py` cycle, a summary report:
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
- Try increasing wait time in `gemini_client.py`

**Telegram not sending**
- Verify bot token is correct in `.env`
- Ensure chat ID is correct
- Bot must have permission to message your chat

**Browser won't launch**
- Install/verify Brave path in `config.py`
- On Linux: `sudo apt install brave-browser`

**Proxy validation fails**
- Check `proxies/proxyscrape_raw.txt` exists
- Verify internet connection
- Proxies may be blocked by the test URL

---

## Project Structure

```
.
├── analyzer.py           # AI job analyzer (Gemini)
├── config.py             # Configuration
├── gemini_client.py      # Browser automation for Gemini
├── job_loader.py         # JSONL loader
├── profile.txt           # Your CV
├── requirements.txt      # Dependencies
├── run_daily.py          # Scheduler (scraper + analyzer)
├── scraper.py            # Job scraper
├── telegram_notify.py    # Telegram notifications
├── user_profile.py       # CV loader
├── validate_proxies.py   # Proxy validator
├── jobs.jsonl            # Scraped jobs (generated)
├── analysis_results.jsonl # Analysis output
├── cron.log              # Run logs (generated)
├── proxies/
│   ├── proxyscrape_raw.txt # Raw proxy list (provide your own)
│   └── working.txt         # Validated working proxies
├── tests/
│   ├── test_analyzer.py
│   └── test_scraper.py
└── docs/                 # Specs and plans
```

---

## Cron Setup

For automatic hourly scraping + analysis:

```bash
# Edit crontab
crontab -e

# Add this line (runs every 30 minutes)
*/30 * * * * cd /home/can/Desktop/job && /home/can/Desktop/job/.venv/bin/python run_daily.py >> cron.log 2>&1
```

Logs are written to `cron.log` in the project directory.

---

## Configuration

Key settings in `config.py`:

| Setting | Description |
|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token |
| `DEFAULT_CHAT_ID` | Your Telegram chat ID |
| `BROWSER_PROFILE_PATH` | Path to Brave browser profile |
| `PROFILE_FILE` | Path to your CV text file |
| `JOBS_INPUT_FILE` | Default jobs file |
| `ANALYSIS_OUTPUT_FILE` | Analysis results file |
