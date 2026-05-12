"""Helpers for summarizing analyzer output."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from analysis_validation import is_valid_analysis


def count_jsonl_lines(path: str) -> int:
    """Count raw lines in a JSONL file."""
    file_path = Path(path)
    if not file_path.exists():
        return 0

    with file_path.open() as f:
        return sum(1 for _ in f)


def read_jsonl_records(path: str, start_index: int = 0) -> list[dict[str, Any]]:
    """Read JSONL records from a file starting at a raw line offset."""
    file_path = Path(path)
    if not file_path.exists():
        return []

    records: list[dict[str, Any]] = []
    with file_path.open() as f:
        for index, line in enumerate(f):
            if index < start_index:
                continue
            if not line.strip():
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                records.append(parsed)
    return records


def summarize_analysis_results(results: list[dict[str, Any]], analyzer_ok: bool) -> dict[str, Any]:
    """Summarize only the current run's analysis result records.

    Status meanings:
      - no_jobs: analyzer succeeded but produced no new result lines
      - success: all new result lines succeeded
      - partial: some new result lines succeeded and some failed
      - failed: analyzer failed or every new result line failed
    """
    succeeded = 0
    failed = 0
    error_messages: list[str] = []

    for record in results:
        analysis = record.get("analysis")
        error = record.get("error")

        if is_valid_analysis(analysis) and not error:
            succeeded += 1
            continue

        failed += 1
        if error:
            error_messages.append(str(error))
        else:
            error_messages.append("Missing or invalid analysis data in result record")

    processed = succeeded + failed

    if not analyzer_ok:
        status = "failed"
    elif processed == 0:
        status = "no_jobs"
    elif failed == 0:
        status = "success"
    elif succeeded == 0:
        status = "failed"
    else:
        status = "partial"

    error_summary = None
    if status == "partial" and failed > 0:
        first_error = error_messages[0] if error_messages else "Unknown error"
        error_summary = f"{failed} of {processed} jobs failed. First error: {first_error}"
    elif status == "failed" and processed > 0 and failed == processed:
        first_error = error_messages[0] if error_messages else "Unknown error"
        error_summary = f"All {processed} jobs failed. First error: {first_error}"

    return {
        "processed": processed,
        "succeeded": succeeded,
        "failed": failed,
        "status": status,
        "error_summary": error_summary,
    }
