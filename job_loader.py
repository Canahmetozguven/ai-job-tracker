"""Job loader from JSON Lines file."""

import json
import math
from typing import Iterator, Dict


def _sanitize(value):
    """Strip NaN floats that may have leaked in from a previous scraper run.

    Python's ``json`` accepts the literal ``NaN`` (a float) and round-trips it
    through ``json.dumps`` as ``NaN`` (illegal JSON). We normalize any float
    NaN to ``None`` so downstream code can use ``or 'N/A'`` patterns safely
    and the output JSONL stays valid.
    """
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _sanitize_record(record: Dict) -> Dict:
    return {k: _sanitize(v) for k, v in record.items()}


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
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict):
                yield _sanitize_record(record)

def count_jobs(path: str) -> int:
    """Count total jobs in file."""
    count = 0
    for _ in load_jobs(path):
        count += 1
    return count