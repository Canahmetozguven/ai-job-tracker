# Job Analyzer with Gemini AI

Browser-based job posting analyzer that uses AI to evaluate job fit based on your CV/profile, then sends results to Telegram.

## How It Works

1. Loads your CV from `profile.txt`
2. Reads job listings from a JSONL file
3. Uses **Camoufox** (Playwright) to control Brave browser
4. Sends each job to Gemini with your profile context
5. Parses Gemini's response and sends formatted results to Telegram

## Project Structure

```
job_analyzer/
├── analyzer.py           # Main CLI script
├── config.py             # Configuration (tokens, paths, prompts)
├── user_profile.py       # CV/profile loader
├── job_loader.py         # JSONL job file loader
├── telegram_notify.py     # Telegram sending & formatting
├── gemini_client.py      # Browser automation for Gemini
├── profile.txt           # Your CV (plain text)
├── jobs.jsonl            # Job listings input
└── tests/
    └── test_analyzer.py  # Unit tests
```

## Setup

### 1. Install Dependencies

```bash
uv pip install camoufox playwright python-telegram-bot python-dotenv
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```bash
TELEGRAM_BOT_TOKEN=your-bot-token-here
```

### 3. Configure Browser Profile (Optional)

Edit `config.py` with your browser profile path:

### 2. Configure

Edit `config.py` with your settings:

```python
TELEGRAM_BOT_TOKEN = "your-bot-token"
BROWSER_PROFILE_PATH = "path/to/your/Brave/User Data"
DEFAULT_CHAT_ID = "your-telegram-chat-id"
```

### 3. Add Your CV

Edit `profile.txt` with your CV as plain text. The analyzer includes this in every Gemini prompt.

### 4. Get Telegram Chat ID

Message [@userinfobot](https://t.me/userinfobot) on Telegram to get your chat ID.

### 5. Prepare Job Listings

Job files must be JSONL format (one JSON object per line):

```json
{"title": "Data Scientist", "company": "Acme", "location": "Remote", "job_url": "https://...", "description": "Job description..."}
```

## Usage

```bash
# Analyze 1 job (dry run)
uv run python analyzer.py --jobs jobs.jsonl --limit 1

# Analyze all jobs in file
uv run python analyzer.py --jobs jobs.jsonl

# Use specific job file
uv run python analyzer.py --jobs jobs_turkey.jsonl

# Analyze and save results
uv run python analyzer.py --jobs jobs.jsonl --output my_results.jsonl
```

### Command Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--jobs` | `jobs.jsonl` | Job listings file |
| `--profile` | `profile.txt` | Your CV/profile file |
| `--limit` | `0` (all) | Max jobs to process |
| `--output` | `analysis_results.jsonl` | Results output file |
| `--browser-path` | from config | Browser profile directory |

## Output

Results are saved to `analysis_results.jsonl` in JSONL format:

```json
{"job": {"title": "...", "company": "...", ...}, "analysis": {"score": "8/10", "why_good": "...", "why_bad": "...", "recommendation": "Apply"}}
```

Each analyzed job is also sent to Telegram as a formatted message.

## Gemini Response Format

The analyzer expects Gemini to respond in this format:

```
1. FIT SCORE: X/10
2. WHY GOOD: ...
3. WHY BAD: ...
4. RECOMMENDATION: Apply/Skip/Review
```

## Browser Setup

The analyzer uses Camoufox (Playwright) with Brave browser. It loads your existing browser profile so you stay logged into Gemini.

### Brave Installation (if needed)

```bash
# Linux
sudo apt install brave-browser

# Or download from brave.com
```

### Browser Profile

The analyzer needs a browser profile that's logged into Gemini. You can:
- Use your existing Brave profile (`User Data/Default`)
- Copy the profile path to `BROWSER_PROFILE_PATH` in config

## Troubleshooting

**"No response received"**
- Check Gemini is accessible: https://gemini.google.com/app
- Verify browser profile is logged in
- Try increasing wait time in `gemini_client.py`

**Telegram not sending**
- Verify bot token is correct
- Ensure chat ID is correct
- Check bot has permission to message your chat

**Browser won't launch**
- Install Brave system-wide or update `executable_path` in `gemini_client.py`
- Ensure browser profile path exists

## Testing

```bash
uv run pytest tests/test_analyzer.py -v
```

## License

MIT