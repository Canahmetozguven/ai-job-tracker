# Job Analyzer with Gemini AI - Design

## Overview

A system that uses Camufix (browser automation) to control a Chrome/Brave browser with your authenticated session, navigates to Gemini, analyzes job postings for fit, and sends results to Telegram.

## Components

```
jobs.jsonl → Job Analyzer → Gemini (browser) → Telegram Bot → Your Chat
                  ↑
              profile.txt
```

## Architecture

### Files
- `analyzer.py` - Main job analyzer script
- `profile.txt` - Your profile info (skills, experience, requirements)
- `jobs.jsonl` - Input job data (from scraper)
- `analysis_results.jsonl` - Output with AI evaluations

### Browser Setup (Camufix)
- Profile path: `USER_INFO_BACKUP_DESKTOP-MR1KOEH/Brave/User Data`
- Load existing session for authenticated Gemini access
- No login needed if session is valid

### Telegram Integration
- Bot token: `8647111790:AAEkQaOy9JbqYVXRfDCYBHhnJS97VzHif_w`
- Send formatted results to configured chat ID

### Flow
1. Load profile from `profile.txt`
2. For each job in `jobs.jsonl`:
   - Build prompt with job + profile
   - Open Gemini chat in browser
   - Submit prompt, wait for response
   - Parse response for fit score + explanation
   - Send to Telegram

## Configuration

| Item | Source |
|------|--------|
| Browser profile | `USER_INFO_BACKUP_DESKTOP-MR1KOEH/Brave/User Data` |
| Telegram bot | `8647111790:AAEkQaOy9JbqYVXRfDCYBHhnJS97VzHif_w` |
| Profile data | `profile.txt` (user provides) |

## Prompt Template

```
Analyze this job posting for fit with my profile.

MY PROFILE:
{profile_text}

JOB INFO:
Title: {title}
Company: {company}
Location: {location}
URL: {url}

Description:
{description}

Respond with:
1. FIT SCORE: X/10
2. WHY GOOD: ...
3. WHY BAD: ...
4. RECOMMENDATION: Apply/Skip/Review
```

## Dependencies

- camufix (browser automation)
- python-telegram-bot (for sending messages)
- job data from scraper