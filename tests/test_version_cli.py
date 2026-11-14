"""Integration tests for the `--version` flag."""

from __future__ import annotations

from .cli_runner import run_cli


def test_version_prints_package_and_bundled_tool_versions() -> None:
    result = run_cli("--version")

    assert result.returncode == 0, result.stderr
    line = result.stdout.strip()
    assert line.startswith("python-linters ")
    assert "(ruff " in line
    assert ", ty " in line
    assert ", pymodularity " in line
