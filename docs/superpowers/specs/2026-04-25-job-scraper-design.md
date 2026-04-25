# Job Scraper Design

## Overview

A CLI tool that scrapes jobs using both `linkedin-scraper` and `JobSpy` libraries, outputting to JSON Lines format with JobSpy as primary source and LinkedIn-scraper as fallback.

## Architecture

```
┌─────────────────────────────────────────────┐
│                 CLI Menu                     │
│  - Interactive prompts for search params     │
│  - Source selection (LinkedIn / JobSpy / Both)│
└──────────────────┬──────────────────────────┘
                   │
       ┌───────────┴───────────┐
       ▼                       ▼
┌──────────────┐      ┌──────────────┐
│   JobSpy     │      │ LinkedIn     │
│  (Primary)   │      │  (Fallback)  │
│              │      │              │
│ - indeed     │      │ - Requires   │
│ - linkedin   │      │   session    │
│ - zip_recruiter      │ - Richer data│
│ - glassdoor  │      └──────┬───────┘
│ - google     │             │
└──────┬───────┘             │
       │                    │
       └────────┬───────────┘
                ▼
      ┌─────────────────┐
      │  Deduplicate    │
      │  by job_url     │
      └────────┬────────┘
               ▼
      ┌─────────────────┐
      │  JSON Lines     │
      │  output file    │
      └─────────────────┘
```

## Data Model

Each job in the output file follows this schema:

```json
{
  "title": "Software Engineer",
  "company": "Company Name",
  "location": "San Francisco, CA",
  "job_url": "https://...",
  "description": "Full description text...",
  "date_posted": "2026-04-25",
  "job_type": "fulltime",
  "salary": {"min": 100000, "max": 150000, "currency": "USD"},
  "source": "indeed",
  "is_remote": false
}
```

## CLI Menu Flow

1. **Search Query** → Enter job title/keywords
2. **Location** → Enter location (city, state/country)
3. **Sources** → Choose:
   - `[1]` JobSpy only (default)
   - `[2]` LinkedIn-scraper only
   - `[3]` Both with fallback (JobSpy → LinkedIn on failure)
4. **Results Limit** → Number of jobs per source
5. **Output File** → Output path (default: `jobs.jsonl`)

## Fallback Logic

- **JobSpy primary**: Tries first, if it fails or returns <5 jobs, try LinkedIn-scraper
- **LinkedIn secondary**: Only used as fallback; requires session.json auth
- **Graceful degradation**: If LinkedIn fails, return JobSpy results only (never error out entirely)

## Dependencies

- `python-jobspy` (JobSpy)
- `linkedin-scraper` v3.x
- `playwright` (for LinkedIn-scraper)

## Output

One JSON object per line in JSON Lines format. Fields may be `null` if unavailable from source.