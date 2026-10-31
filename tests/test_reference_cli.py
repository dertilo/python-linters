"""Integration tests for the `reference` subcommand."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .cli_runner import run_cli

if TYPE_CHECKING:
    import subprocess


def _run_reference(tool: str) -> subprocess.CompletedProcess[str]:
    return run_cli("reference", tool)


def test_reference_ruff_prints_shipped_config() -> None:
    result = _run_reference("ruff")

    assert result.returncode == 0, result.stderr
    assert "Ruff Reference Configuration" in result.stdout
    assert "[lint]" in result.stdout


def test_reference_ty_prints_shipped_config() -> None:
    result = _run_reference("ty")

    assert result.returncode == 0, result.stderr
    assert "ty Reference Configuration" in result.stdout
    assert "[rules]" in result.stdout


def test_reference_unknown_tool_is_rejected() -> None:
    result = _run_reference("eslint")

    assert result.returncode == 2
    assert "invalid choice" in result.stderr
