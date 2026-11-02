"""Integration tests for the `check-config` subcommand.

Uses the package's own shipped references as fixtures: both must already be
triaged clean against the pinned tool versions (python-linters' own release
gate), and a copy with one rule name deleted must report that exact name.
"""

from __future__ import annotations

import importlib.resources
from pathlib import Path
from typing import TYPE_CHECKING

from .cli_runner import run_cli

if TYPE_CHECKING:
    import subprocess


def _run_check_config(tool: str, config: Path) -> subprocess.CompletedProcess[str]:
    return run_cli("check-config", tool, str(config))


def _reference_path(tool: str) -> Path:
    filename = {"ruff": "ruff.reference.toml", "ty": "ty.reference.toml"}[tool]
    # python-linters always ships as a real filesystem package (never a
    # zipped wheel on sys.path), so this Traversable is always a real Path.
    return Path(
        str(importlib.resources.files("python_linters.references").joinpath(filename))
    )


def test_check_config_ruff_reference_is_clean() -> None:
    result = _run_check_config("ruff", _reference_path("ruff"))

    assert result.returncode == 0, result.stdout + result.stderr
    assert "up to date" in result.stdout


def test_check_config_ty_reference_is_clean() -> None:
    result = _run_check_config("ty", _reference_path("ty"))

    assert result.returncode == 0, result.stdout + result.stderr
    assert "up to date" in result.stdout


def test_check_config_ruff_missing_category_exits_one_and_names_it(
    tmp_path: Path,
) -> None:
    content = _reference_path("ruff").read_text()
    line = '    "PD",    # pandas-vet — common pandas antipatterns\n'
    assert line in content
    config = tmp_path / "ruff.toml"
    config.write_text(content.replace(line, ""))

    result = _run_check_config("ruff", config)

    assert result.returncode == 1
    assert '"PD"' in result.stdout


def test_check_config_ty_missing_rule_exits_one_and_names_it(tmp_path: Path) -> None:
    content = _reference_path("ty").read_text()
    line = 'redundant-cast = "error"\n'
    assert line in content
    config = tmp_path / "ty.toml"
    config.write_text(content.replace(line, ""))

    result = _run_check_config("ty", config)

    assert result.returncode == 1
    assert "redundant-cast" in result.stdout


def test_check_config_single_letter_prefix_does_not_cover_other_linter(
    tmp_path: Path,
) -> None:
    """ "N" (pep8-naming) must not be read as covering "NPY" (NumPy) just
    because "NPY" starts with "N": they are different linters."""
    content = _reference_path("ruff").read_text()
    line = '    "NPY",   # NumPy-specific rules — deprecated NumPy aliases\n'
    assert line in content
    config = tmp_path / "ruff.toml"
    config.write_text(content.replace(line, ""))

    result = _run_check_config("ruff", config)

    assert result.returncode == 1
    assert '"NPY"' in result.stdout


def test_check_config_missing_file_exits_two(tmp_path: Path) -> None:
    result = _run_check_config("ruff", tmp_path / "does-not-exist.toml")

    assert result.returncode == 2
    assert "not found" in result.stderr
