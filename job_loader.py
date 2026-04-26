"""Job loader from JSON Lines file."""

import json
from typing import Iterator, Dict

def load_jobs(path: str) -> Iterator[Dict]:
    """Load jobs from jsonl file.

    Args:
        path: Path to jobs.jsonl file

    Yields:
        Job dict with title, company, location, description, job_url, etc.
    """
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue

def count_jobs(path: str) -> int:
    """Count total jobs in file."""
    count = 0
    for _ in load_jobs(path):
        count += 1
    return count