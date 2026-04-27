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
| `profile.txt` | Your CV as plain text |

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

### Daily Runner

Combines scraper + analyzer in sequence with retry support:

```bash
# Single run
uv run python run_daily.py

# For cron (runs every 30 minutes)
*/30 * * * * cd /home/can/Desktop/job && /usr/bin/python3 run_daily.py >> cron.log 2>&1
```

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

## Troubleshooting

**Scraper returns 0 jobs**
- Check proxy list: `proxies/working.txt`
- LinkedIn may require session.json for authentication

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
├── jobs.jsonl            # Scraped jobs (generated)
├── analysis_results.jsonl # Analysis output
├── proxies/
│   └── working.txt       # Working proxy list
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
*/30 * * * * cd /home/can/Desktop/job && /usr/bin/python3 run_daily.py >> cron.log 2>&1
```

Logs are written to `cron.log` in the project directory.
