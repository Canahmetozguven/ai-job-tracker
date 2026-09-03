#!/usr/bin/env python3
"""Reject high-confidence credentials in tracked or supplied text files."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


TELEGRAM_TOKEN = re.compile(r"\b\d{8,10}:" + r"[A-Za-z0-9_-]{30,}\b")
PRIVATE_KEY = re.compile(
    r"-----BEGIN (?:(?:DSA|EC|ENCRYPTED|OPENSSH|RSA) )?PRIVATE KEY-----"
)
CREDENTIAL_ASSIGNMENT = re.compile(
    r"(?i)(?<![A-Za-z0-9_])(?:[A-Za-z0-9]+[_-])*"
    r"(?:api[_-]?key|access[_-]?token|bot[_-]?token|password|secret)"
    r"(?:[_-][A-Za-z0-9]+)*"
    r"(?![A-Za-z0-9_])"
    r"[\"']?\s*[:=]\s*"
    # Quoted values may hold any punctuation; bare values stay token-shaped.
    r"(?:[\"']([^\"'\n]{20,})[\"']|([A-Za-z0-9_./+=-]{20,}))"
)
PLACEHOLDERS = ("example", "placeholder", "redacted", "your-")


def find_secrets(text: str) -> list[str]:
    """Return names of high-confidence secret patterns found in ``text``."""
    findings = []
    if TELEGRAM_TOKEN.search(text):
        findings.append("Telegram bot token")
    if PRIVATE_KEY.search(text):
        findings.append("private key")
    for match in CREDENTIAL_ASSIGNMENT.finditer(text):
        candidate = (match.group(1) or match.group(2)).lower()
        if not any(marker in candidate for marker in PLACEHOLDERS):
            findings.append("credential assignment")
            break
    return findings


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        check=True,
        capture_output=True,
    )
    return [path.decode() for path in result.stdout.split(b"\0") if path]


def main(paths: list[str] | None = None) -> int:
    failures = []
    for filename in paths or tracked_files():
        path = Path(filename)
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for finding in find_secrets(text):
            failures.append(f"{path}: possible {finding}")

    if failures:
        print("Secret scan failed:", file=sys.stderr)
        print("\n".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:] or None))
