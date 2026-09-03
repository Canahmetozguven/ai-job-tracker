"""Shared test fixtures.

Note this is not the `sys.path` shim that used to live here — the project is
installed now, so imports need no help. This exists only to make Typer's
Rich-rendered output deterministic across environments.
"""

import re

import pytest
from typer.testing import CliRunner

# Rich splits styled text mid-token: `--query` renders as
# "\x1b[1;36m-\x1b[0m\x1b[1;36m-query\x1b[0m", so a plain `"--query" in output`
# check fails. Rich also force-enables colour when GITHUB_ACTIONS is set, which
# made this pass locally and fail only on CI.
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

# A wide terminal stops Rich wrapping option names into the help's next line.
CLI_ENV = {"NO_COLOR": "1", "TERM": "dumb", "COLUMNS": "200"}


def plain(text: str) -> str:
    """Strip ANSI styling so assertions match what a reader sees."""
    return ANSI_RE.sub("", text)


@pytest.fixture
def cli():
    """A CliRunner whose output is stable regardless of terminal or CI."""
    return CliRunner(env=CLI_ENV)
