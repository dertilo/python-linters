"""Run ruff, ruff format --check, ty and pymodularity and group their findings by rule.

Ported from lint_grouped.py (quality-and-security-tools howtos), minus eslint.

Output structure:
    {
      "project": "/abs/path",
      "summary": {
        "ruff":        {"total": 100, "rules": 12},
        "ruff-format": {"total": 2,   "rules": 1},
        "ty":          {"total": 50,  "rules": 8},
        "pymodularity": {"total": 5,  "rules": 2}
      },
      "ruff": {
        "ANN001": {
          "url":       "https://docs.astral.sh/ruff/rules/...",
          "count":     42,
          "locations": [{"file": "rel/path.py", "line": 12, "col": 5, "message": "..."}, ...]
        }
      },
      "ruff-format": {
        "unformatted": {
          "count":     2,
          "locations": [{"file": "rel/path.py", "line": 1, "col": 1, "message": "would be reformatted"}, ...]
        }
      },
      "ty": {
        "invalid-return-type": {
          "severity":  "major",
          "count":     15,
          "locations": [{"file": "rel/path.py", "line": 7, "col": 1, "message": "..."}, ...]
        }
      },
      "pymodularity": {
        "import-cycle": {
          "url":       "https://.../rules.md#...",
          "count":     3,
          "locations": [{"file": "rel/path.py", "line": 0, "col": 0, "message": "..."}, ...]
        }
      }
    }

Rules are sorted by count (descending) so the most common issues come first.
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from python_linters.tool_errors import ToolFailedError, run_checked

if TYPE_CHECKING:
    from collections.abc import Iterable

_TY_SEVERITY_MAP = {"major": "error", "minor": "warning", "info": "info"}

# Matches ruff format --check's per-file location line, e.g.:
#  --> my_package/main_module.py:1:2
_RUFF_FORMAT_LOCATION_RE = re.compile(r"^ --> (?P<file>.+):(?P<line>\d+):(?P<col>\d+)$")


@dataclass
class Location:
    file: str
    line: int
    col: int
    message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "file": self.file,
            "line": self.line,
            "col": self.col,
            "message": self.message,
        }


@dataclass
class FindingGroup:
    """One rule's findings: ruff/pymodularity carry a `url`, ty a `severity`."""

    url: str | None = None
    severity: str | None = None
    count: int = 0
    locations: list[Location] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        out: dict[str, object] = {}
        if self.url is not None:
            out["url"] = self.url
        if self.severity is not None:
            out["severity"] = self.severity
        out["count"] = self.count
        out["locations"] = [location.to_dict() for location in self.locations]
        return out


# A finding on its way into a rule group: (rule key, its url or None, its
# severity or None, the one location this finding adds).
_Finding = tuple[str, str | None, str | None, Location]


def _group_findings(findings: Iterable[_Finding]) -> dict[str, FindingGroup]:
    """Group findings by rule, each group carrying a count and its locations.

    The one grouping loop shared by ruff, ty and pymodularity — each tool
    only maps its own diagnostics into `_Finding` tuples first.
    """
    grouped: dict[str, FindingGroup] = {}
    for rule, url, severity, location in findings:
        group = grouped.setdefault(rule, FindingGroup(url=url, severity=severity))
        group.count += 1
        group.locations.append(location)

    return dict(sorted(grouped.items(), key=lambda item: item[1].count, reverse=True))


def _relative_to(path_str: str, project_path: Path) -> str:
    try:
        return str(Path(path_str).relative_to(project_path))
    except ValueError:
        return path_str


def run_ruff(project_path: Path) -> dict[str, FindingGroup]:
    # Resolution: the python-linters environment's own pinned ruff, run as
    # `sys.executable -m ruff` so it never falls through to PATH. In
    # dev-dependency mode that environment is the linted project's venv, so
    # ruff==0.17.5 (pinned in python-linters' own pyproject.toml) is what
    # actually runs — never a PATH ruff of another version, which lints
    # with other rules and may refuse the reference config.
    #
    # ruff's exit codes: 0 clean, 1 findings, 2 tool failure (unknown rule
    # selector, bad config, ...). Empty stdout on exit 2 must never read
    # as "0 findings" — `run_checked` raises instead of returning in that case.
    result = run_checked(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--no-cache",
            "--output-format",
            "json",
            ".",
        ],
        project_path,
        "ruff",
        ok_codes=(0, 1),
    )
    if not result.stdout.strip():
        return {}

    diagnostics = json.loads(result.stdout)

    def findings() -> Iterable[_Finding]:
        for d in diagnostics:
            code = d.get("code") or "unknown"
            location = Location(
                file=_relative_to(d["filename"], project_path),
                line=d["location"]["row"],
                col=d["location"]["column"],
                message=d["message"],
            )
            yield code, d.get("url", ""), None, location

    return _group_findings(findings())


def run_ruff_format(project_path: Path) -> dict[str, FindingGroup]:
    # Resolution: same as run_ruff above — `sys.executable -m ruff`, never
    # PATH, `--no-cache` so a read-only linted project tree is never an
    # issue.
    #
    # `ruff format --check` has no JSON output mode (unlike `ruff check`):
    # `ruff format --help` lists `--output-format` only under `check`, not
    # under `format`. Its human-readable stdout does carry one `-->
    # path:line:col` line per unformatted file, which is parsed below
    # instead.
    #
    # ruff format's exit codes: 0 all formatted, 1 some file would be
    # reformatted, 2 tool failure (bad config, crash, ...). A failure must
    # never read as "0 findings" — `run_checked` raises instead of
    # returning in that case.
    result = run_checked(
        [sys.executable, "-m", "ruff", "format", "--check", "--no-cache", "."],
        project_path,
        "ruff-format",
        ok_codes=(0, 1),
    )
    if not result.stdout.strip():
        return {}

    def findings() -> Iterable[_Finding]:
        for line in result.stdout.splitlines():
            match = _RUFF_FORMAT_LOCATION_RE.match(line)
            if match is None:
                continue
            location = Location(
                file=_relative_to(match["file"], project_path),
                line=int(match["line"]),
                col=int(match["col"]),
                message="would be reformatted",
            )
            yield "unformatted", None, None, location

    groups = _group_findings(findings())
    # Exit 1 with nothing parsed means ruff changed its text output: fail
    # loudly instead of reporting a clean project.
    if result.returncode == 1 and not groups:
        detail = f"exit 1 but no ' --> path:line:col' line parsed:\n{result.stdout}"
        tool = "ruff-format"
        raise ToolFailedError(tool, detail)
    return groups


def run_ty(project_path: Path) -> dict[str, FindingGroup]:
    # Resolution: `sys.executable -m ty` from the python-linters
    # environment, never a bare `ty` entry point (that one falls through to
    # PATH when the environment has no ty on it) and never a PATH `ty`.
    # In dev-dependency mode that environment is the linted project's own
    # venv, so ty also sees the project's installed packages for
    # resolution.
    #
    # Output format: `gitlab` — the only ty format that is both
    # machine-readable JSON and carries rule id, severity, file, line and
    # column, which is what the merged-JSON shape below needs. (`json` does
    # not exist as a ty output format; `full`/`concise` are human text.)
    #
    # ty's own exit codes: 0 clean, 1 findings, 2 tool failure (bad config,
    # crash, ...). A failure must never read as "0 findings" — that reversed
    # a `ty` config bug into a silent clean bill in review.
    #
    # Environment: `uv run` sets VIRTUAL_ENV to python-linters' own venv,
    # and ty's environment discovery reads VIRTUAL_ENV *before* looking for
    # a `.venv` under cwd — unlike `sys.executable`, picking the wrong env
    # doesn't depend on which env actually ran this process. Left alone,
    # ty resolves the linted project's imports (e.g. `import attrs`)
    # against python-linters' own env instead of the project's, and
    # reports them as unresolved-import false positives. Dropping
    # VIRTUAL_ENV here makes ty fall through to discovering `.venv` under
    # project_path itself. In dev-dependency mode this is a no-op: there
    # the project's own venv was VIRTUAL_ENV already.
    ty_env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    result = run_checked(
        [sys.executable, "-m", "ty", "check", "--output-format", "gitlab", "."],
        project_path,
        "ty",
        ok_codes=(0, 1),
        env=ty_env,
    )
    if not result.stdout.strip():
        return {}

    diagnostics = json.loads(result.stdout)

    def findings() -> Iterable[_Finding]:
        # GitLab labels severities major/minor/info; ty itself says
        # error/warning/info. Map back so a reader sees the same words
        # `ty check` would have printed.
        for d in diagnostics:
            rule = d.get("check_name") or "unknown"

            location_data = d.get("location", {})
            start = location_data.get("positions", {}).get("begin", {})

            # GitLab's description already starts with "<check_name>: ",
            # which would otherwise repeat the rule id inside every message.
            description = d.get("description", "")
            description = description.removeprefix(f"{rule}: ")

            severity = _TY_SEVERITY_MAP.get(d.get("severity", "major"), "error")
            location = Location(
                # GitLab paths are already relative to cwd (= project_path,
                # since ty runs with cwd=project_path), so no relative_to()
                # call is needed here.
                file=location_data.get("path", ""),
                line=start.get("line", 1),
                col=start.get("column", 1),
                message=description,
            )
            yield rule, None, severity, location

    return _group_findings(findings())


def run_pymodularity(project_path: Path) -> dict[str, FindingGroup]:
    # Resolution: `sys.executable -m pymodularity`, same reasoning as ruff
    # and ty above — the python-linters environment's own pinned install,
    # never PATH.
    #
    # pymodularity's exit codes: 0 empty array, 1 at least one finding,
    # 2 `uv` missing or an uncaught exception (docs/rules.md "JSON output").
    # A failure must never read as "0 findings".
    result = run_checked(
        [
            sys.executable,
            "-m",
            "pymodularity",
            "check",
            "--output-format",
            "json",
            str(project_path),
        ],
        project_path,
        "pymodularity",
        ok_codes=(0, 1),
    )
    if not result.stdout.strip():
        return {}

    findings_data = json.loads(result.stdout)

    def findings() -> Iterable[_Finding]:
        for f in findings_data:
            rule = f.get("rule") or "unknown"
            # pymodularity's `path` key maps to `file` here, to match the
            # ruff and ty groups above.
            location = Location(
                file=f.get("path", ""),
                line=f.get("line", 0),
                col=f.get("col", 0),
                message=f.get("message", ""),
            )
            yield rule, f.get("url", ""), None, location

    return _group_findings(findings())


def build_report(project_path: Path) -> tuple[dict[str, object], int]:
    """Return the JSON-ready report and the total finding count across all tools."""
    summary: dict[str, object] = {}
    sections: dict[str, object] = {}
    grand_total = 0

    for tool, run in (
        ("ruff", run_ruff),
        ("ruff-format", run_ruff_format),
        ("ty", run_ty),
        ("pymodularity", run_pymodularity),
    ):
        print(f"Running {tool} on {project_path} ...", file=sys.stderr)
        violations = run(project_path)
        total = sum(group.count for group in violations.values())
        print(f"  {total} violations across {len(violations)} rules", file=sys.stderr)

        summary[tool] = {"total": total, "rules": len(violations)}
        sections[tool] = {rule: group.to_dict() for rule, group in violations.items()}
        grand_total += total

    report = {"project": str(project_path), "summary": summary, **sections}
    return report, grand_total
