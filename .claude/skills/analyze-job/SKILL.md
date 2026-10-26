---
name: analyze-job
description: Analyze a single job posting against the user's profile and return a structured fitness assessment.
---

# Analyze Job Posting

Analyze a single job posting against the user's profile and return a structured fitness assessment.

## Input

The user provides job details — at minimum a title and company. They may paste a full posting, a URL, or a JSON object with fields: `title`, `company`, `location`, `job_url`, `description`.

## Steps

1. Read `profile.txt` (or the path in `PROFILE_FILE` from `.env`) from the project root. If it doesn't exist, ask the user for their profile or CV text.

2. Build the analysis prompt using the template below, filling in the profile and job fields. Truncate description to 2000 characters.

3. Analyze the job against the profile. Score fit strictly using evidence from the profile and description only.

4. Return the result in **exactly** this format — nothing else:

```
FIT SCORE: X/10
WHY GOOD: <concise bullets>
WHY BAD: <concise bullets>
RECOMMENDATION: <Apply|Review|Skip> — <one short next step>
```

## Prompt Template

```
Analyze this job posting for an actionable shortlist decision.

MY PROFILE:
{profile}

JOB INFO:
Title: {title}
Company: {company}
Location: {location}
URL: {url}

Description:
{description}

Guidance:
- Score fit strictly using evidence from the profile and description only. Do not inflate scores for vague overlap.
- **Data-role boost:** For any job whose title contains one of the following, you MUST score it 6+/10 even if only loosely or tangentially related. This is a mandatory floor, not a suggestion: data engineer, data analyst, analytics, BI analyst, business analyst, ML engineer, ML ops, AI engineer, LLM engineer, deep learning, NLP engineer, data infrastructure, ETL/data warehouse, data platform, BI engineer.
- **Data Science priority:** If the job title contains "Data Science" or "Data Scientist", score it 9/10 or 10/10. **Exception:** If hard dealbreakers exist, reduce the score but never go below 6+/10 — this is a mandatory minimum floor. Always flag dealbreakers prominently in why_bad.
- **Strategic Edge:** Flag in why_good if the role involves HealthTech, behavioral analytics, LLM integration, or international/remote setups where my unique background is an asset.
- Make why_good concise: short bullets or phrases explaining why this is worth applying to now.
- Make why_bad concise: include gaps, dealbreakers, mandatory language requirements, visa/relocation hurdles, or missing tech stacks.
- recommendation must be exactly one of Apply, Review, or Skip. Add one short next step after the keyword if possible, like "Apply — tailor resume" or "Review — confirm visa sponsorship".
```

## Scoring Rules

- `score`: format `X/10` where X is 1-10.
- `recommendation`: exactly one of `Apply`, `Review`, or `Skip`, optionally followed by ` — <next step>`.
- Big Tech companies (Apple, Microsoft, Google/Alphabet, Amazon/AWS, Meta, Nvidia, Tesla) should be flagged in why_good.
