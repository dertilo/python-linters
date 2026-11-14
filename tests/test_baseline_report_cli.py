"""Integration tests: `lint --baseline REF` on a real temp git repo."""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import TYPE_CHECKING

from .cli_runner import run_cli

if TYPE_CHECKING:
    from pathlib import Path

# Resolved once to a full path: a bare "git" is a partial-executable-path finding.
_GIT = shutil.which("git") or "git"


def _run_lint(*args: str) -> subprocess.CompletedProcess[str]:
    return run_cli("lint", *args)


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]  # fixed git subcommand list, never shell-interpolated or from untrusted input
        [_GIT, *args], cwd=cwd, check=True, capture_output=True, text=True
    )


def _init_repo(project: Path) -> None:
    project.mkdir(parents=True, exist_ok=True)
    (project / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\nrequires-python = ">=3.11"\n'
    )
    pkg = project / "my_package"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    _git("init", "-q", cwd=project)
    _git("config", "user.email", "test@example.com", cwd=project)
    _git("config", "user.name", "test", cwd=project)


def test_lint_baseline_reports_only_new_findings(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    _init_repo(project)
    main_module = project / "my_package" / "main_module.py"

    # Baseline: one unused import (ruff F401).
    main_module.write_text("import os\n\n\ndef noop() -> None:\n    pass\n")
    _git("add", "-A", cwd=project)
    _git("commit", "-q", "-m", "baseline", cwd=project)
    baseline_sha = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]  # fixed git subcommand list, never shell-interpolated or from untrusted input
        [_GIT, "rev-parse", "HEAD"],
        cwd=project,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    # Current: the same unused import, shifted two lines down by an insert
    # above it (must NOT count as new — line is excluded from the key),
    # plus one genuinely new unused import.
    main_module.write_text(
        "\n\nimport os\nimport sys\n\n\ndef noop() -> None:\n    pass\n"
    )
    _git("add", "-A", cwd=project)
    _git("commit", "-q", "-m", "shift + new finding", cwd=project)

    result = _run_lint(
        str(project),
        "--baseline",
        baseline_sha,
        "--skip",
        "ty",
        "--skip",
        "ruff-format",
        "--skip",
        "pymodularity",
    )

    assert result.returncode == 1, result.stderr
    report = json.loads(result.stdout)
    assert report["baseline"] == {"ref": baseline_sha, "sha": baseline_sha}
    assert report["summary"]["ruff"]["total"] == 1
    (location,) = report["ruff"]["F401"]["locations"]
    assert "sys" in location["message"]


def test_lint_baseline_unresolvable_ref_exits_2(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    _init_repo(project)
    (project / "my_package" / "main_module.py").write_text("x = 1\n")
    _git("add", "-A", cwd=project)
    _git("commit", "-q", "-m", "initial", cwd=project)

    result = _run_lint(str(project), "--baseline", "not-a-real-ref")

    assert result.returncode == 2
    assert "not-a-real-ref" in result.stderr


def test_lint_baseline_outside_git_repo_exits_2(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\nrequires-python = ">=3.11"\n'
    )

    result = _run_lint(str(project), "--baseline", "HEAD")

    assert result.returncode == 2
    assert result.stderr.strip() != ""
