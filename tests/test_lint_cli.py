"""Integration tests: run the real CLI on small fixture projects."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .cli_runner import run_cli


def _run_lint(*args: str) -> subprocess.CompletedProcess[str]:
    return run_cli("lint", *args)


def _write_clean_project(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\n'
        'requires-python = ">=3.11"\n'
    )
    (tmp_path / "my_package").mkdir()
    (tmp_path / "my_package" / "__init__.py").write_text("")
    (tmp_path / "my_package" / "main_module.py").write_text(
        "def greet_person(name: str) -> str:\n    return f'hello {name}'\n"
    )
    return tmp_path


def _write_dirty_project(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\n'
        'requires-python = ">=3.11"\n'
    )
    (tmp_path / "my_package").mkdir()
    (tmp_path / "my_package" / "__init__.py").write_text("")
    # unused import (ruff) + bad return type annotation (ty)
    (tmp_path / "my_package" / "main_module.py").write_text(
        "import os\n\n\ndef greet_person(name: str) -> int:\n    return f'hello {name}'\n"
    )
    return tmp_path


def test_lint_clean_project_exits_zero(tmp_path: Path) -> None:
    project = _write_clean_project(tmp_path)

    result = _run_lint(str(project))

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["project"] == str(project)
    assert report["summary"]["ruff"]["total"] == 0
    assert report["summary"]["ty"]["total"] == 0
    assert "pymodularity" in report["summary"]


def test_lint_dirty_project_exits_one_and_groups_by_rule(tmp_path: Path) -> None:
    project = _write_dirty_project(tmp_path)

    result = _run_lint(str(project))

    assert result.returncode == 1, result.stderr
    report = json.loads(result.stdout)
    assert report["summary"]["ruff"]["total"] > 0
    assert report["summary"]["ty"]["total"] > 0

    # ruff's unused-import rule is grouped with a url and locations
    ruff_rules = report["ruff"]
    assert any(
        group["locations"][0]["file"] == "my_package/main_module.py"
        for group in ruff_rules.values()
    )
    assert all("url" in group for group in ruff_rules.values())

    # ty's groups carry a severity instead of a url
    ty_rules = report["ty"]
    assert all("severity" in group for group in ty_rules.values())


def test_lint_defaults_path_to_cwd(tmp_path: Path) -> None:
    project = _write_clean_project(tmp_path)

    result = run_cli("lint", cwd=project)

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["project"] == str(project)


def test_lint_out_writes_report_to_file(tmp_path: Path) -> None:
    project = _write_clean_project(tmp_path)
    out_file = tmp_path / "report.json"

    result = _run_lint(str(project), "--out", str(out_file))

    assert result.returncode == 0, result.stderr
    assert out_file.exists()
    report = json.loads(out_file.read_text())
    assert report["project"] == str(project)


def test_lint_ty_ignores_a_foreign_virtual_env(tmp_path: Path) -> None:
    """`uv run` sets VIRTUAL_ENV to the *runner's* env (python-linters' own
    .venv here), not the linted project's. ty's environment discovery reads
    VIRTUAL_ENV before it looks for a `.venv` under cwd, so a naive ty call
    resolves the project's imports against the wrong env and reports them
    as unresolved-import — reproduced here with a hand-built project .venv
    plus VIRTUAL_ENV pointed at this repo's own, unrelated .venv.
    """
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\n'
        'requires-python = ">=3.11"\n'
    )
    package_dir = project / "typed_package"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text("")
    (package_dir / "main_module.py").write_text(
        "import fixture_dependency\n\nprint(fixture_dependency.VALUE)\n"
    )

    uv_executable = shutil.which("uv")
    assert uv_executable is not None, "uv not found on PATH"
    venv_result = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]  # fixed argv, offline, no network (uv's python is already installed)
        [uv_executable, "venv", str(project / ".venv")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert venv_result.returncode == 0, venv_result.stderr

    site_packages = next((project / ".venv" / "lib").glob("python*")) / "site-packages"
    (site_packages / "fixture_dependency.py").write_text("VALUE = 1\n")

    foreign_env = dict(os.environ)
    foreign_env["VIRTUAL_ENV"] = str(Path(sys.executable).parent.parent)

    result = run_cli("lint", str(project), env=foreign_env)

    assert "unresolved-import" not in result.stdout, result.stdout
    report = json.loads(result.stdout)
    assert report["summary"]["ty"]["total"] == 0


def test_lint_missing_path_exits_two(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"

    result = _run_lint(str(missing))

    assert result.returncode == 2
    assert "does not exist" in result.stderr
