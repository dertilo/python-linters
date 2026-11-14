"""`lint --baseline REF`: report only findings new since a git ref.

Ported from the baseline mode of the semgrep-wrapping gate script, minus
semgrep.

Mechanism:
1. Resolve *ref* to a SHA with `git rev-parse --verify` (a bad ref, or a
   project outside any git repo, fails here).
2. Lint the current tree first, so its resolved ty environment is known.
3. Check out that SHA into a fresh `git worktree add --detach` scratch
   directory — never a reused directory, which can carry stale files from
   an earlier run.
4. Lint the same sub-path inside the worktree, with the same `--skip` set.
   ty's `.venv` discovery has nothing to find in a fresh worktree, so the
   baseline run gets `--python` forwarded explicitly: the caller's own
   `--python` if given, otherwise the current run's resolved
   `ty-environment.python_environment`.
5. Drop every current finding whose (file, rule, message) triple also
   appears at the baseline. The line number is excluded from this key on
   purpose: a finding does not become "new" just because a line was
   inserted above it in the diff's range.
6. Remove the worktree in `finally`, even on a lint failure or a Ctrl-C.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from python_linters.lint_report import TOOL_NAMES, build_report

# Resolved once to a full path: a bare "git" is a partial-executable-path
# finding, and the fallback keeps this working even if `which` ever fails.
_GIT = shutil.which("git") or "git"


class BaselineError(Exception):
    """A baseline ref could not be resolved, or project_path is not in a git repo."""


def _resolve_ref(project_path: Path, ref: str) -> str:
    result = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]  # fixed argv list built by this package, never shell-interpolated or from untrusted input
        [_GIT, "-C", str(project_path), "rev-parse", "--verify", ref],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        msg = f"cannot resolve baseline ref '{ref}': {result.stderr.strip()}"
        raise BaselineError(msg)
    return result.stdout.strip()


def _git_root(project_path: Path) -> Path:
    result = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]  # fixed argv list built by this package, never shell-interpolated or from untrusted input
        [_GIT, "-C", str(project_path), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    return Path(result.stdout.strip())


def _triple(file: str, rule: str, message: str) -> tuple[str, str, str]:
    return (file, rule, message)


def _baseline_triples(report: dict[str, object]) -> set[tuple[str, str, str]]:
    triples: set[tuple[str, str, str]] = set()
    for tool in TOOL_NAMES:
        section = report.get(tool)
        if not isinstance(section, dict):
            continue
        for rule, group in section.items():
            triples.update(
                _triple(loc["file"], rule, loc["message"]) for loc in group["locations"]
            )
    return triples


def _diff_report(
    report: dict[str, object], baseline_triples: set[tuple[str, str, str]]
) -> tuple[dict[str, object], int]:
    """Keep only locations whose triple is not in *baseline_triples*.

    Recomputes each kept rule's `count` and each tool's `summary` entry;
    drops a rule whose locations list becomes empty.
    """
    new_report = dict(report)
    summary: dict[str, object] = {}
    grand_total = 0

    for tool in TOOL_NAMES:
        section = report.get(tool)
        if not isinstance(section, dict):
            continue

        new_section: dict[str, dict[str, object]] = {}
        counts: dict[str, int] = {}
        for rule, group in section.items():
            keep = [
                loc
                for loc in group["locations"]
                if _triple(loc["file"], rule, loc["message"]) not in baseline_triples
            ]
            if not keep:
                continue
            new_group = dict(group)
            new_group["locations"] = keep
            new_group["count"] = len(keep)
            new_section[rule] = new_group
            counts[rule] = len(keep)

        new_report[tool] = new_section
        total = sum(counts.values())
        summary[tool] = {"total": total, "rules": len(new_section)}
        grand_total += total

    new_report["summary"] = summary
    return new_report, grand_total


def run_with_baseline(
    project_path: Path,
    baseline_ref: str,
    skip: frozenset[str] = frozenset(),
    ty_python: str | None = None,
    ty_extra_search_paths: tuple[str, ...] = (),
) -> tuple[dict[str, object], int]:
    """Lint *project_path*, then drop every finding already present at
    *baseline_ref*. Returns the same report shape as `build_report`, plus a
    top-level `"baseline"` key, with the summary and total counting only
    the new findings.

    Raises `BaselineError` if the ref does not resolve or project_path is
    not inside a git repo.
    """
    sha = _resolve_ref(project_path, baseline_ref)
    git_root = _git_root(project_path)
    try:
        rel_to_root = project_path.relative_to(git_root)
    except ValueError:
        rel_to_root = Path()

    current_report, _ = build_report(
        project_path,
        skip=skip,
        ty_python=ty_python,
        ty_extra_search_paths=ty_extra_search_paths,
    )

    # The baseline worktree has no `.venv` of its own to discover: forward
    # the current run's resolved ty environment, unless the caller already
    # pinned one explicitly.
    baseline_ty_python = ty_python
    if baseline_ty_python is None and "ty" not in skip:
        ty_environment = current_report.get("ty-environment", {})
        baseline_ty_python = (
            ty_environment.get("python_environment")
            if isinstance(ty_environment, dict)
            else None
        )

    tmpdir = tempfile.mkdtemp(prefix="python-linters-baseline-")
    try:
        worktree = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]  # fixed argv list built by this package, never shell-interpolated or from untrusted input
            [_GIT, "-C", str(project_path), "worktree", "add", "--detach", tmpdir, sha],
            capture_output=True,
            text=True,
            check=False,
        )
        if worktree.returncode != 0:
            msg = f"git worktree add failed: {worktree.stderr.strip()}"
            raise BaselineError(msg)

        baseline_path = Path(tmpdir) / rel_to_root
        baseline_report, _ = build_report(
            baseline_path,
            skip=skip,
            ty_python=baseline_ty_python,
            ty_extra_search_paths=ty_extra_search_paths,
        )
    finally:
        subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]  # fixed argv list built by this package, never shell-interpolated or from untrusted input
            [_GIT, "-C", str(project_path), "worktree", "remove", "--force", tmpdir],
            capture_output=True,
            text=True,
            check=False,
        )
        shutil.rmtree(tmpdir, ignore_errors=True)

    baseline_triples = _baseline_triples(baseline_report)
    new_report, total = _diff_report(current_report, baseline_triples)
    new_report["baseline"] = {"ref": baseline_ref, "sha": sha}
    if baseline_ty_python is not None:
        new_report["baseline"]["ty-python"] = baseline_ty_python
    return new_report, total
