from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from python_linters.config_check import (
    check_ruff_config,
    check_ty_config,
    format_ruff_report,
    format_ty_report,
)
from python_linters.lint_report import TOOL_NAMES, build_report
from python_linters.reference_files import reference_text
from python_linters.text_report import format_text_report
from python_linters.tool_errors import ToolFailedError
from python_linters.tool_versions import package_version, tool_versions


def _lint(args: argparse.Namespace) -> int:
    if set(args.skip) >= set(TOOL_NAMES):
        args.parser.error("--skip cannot skip every tool")

    project_path = Path(args.path).resolve()
    if not project_path.exists():
        print(f"Error: {project_path} does not exist", file=sys.stderr)
        return 2

    try:
        output, total_findings = build_report(
            project_path,
            skip=frozenset(args.skip),
            ty_python=args.ty_python,
            ty_extra_search_paths=tuple(args.ty_extra_search_path),
        )
    except ToolFailedError as e:
        print(str(e), file=sys.stderr)
        return 2

    serialized = (
        format_text_report(output)
        if args.format == "text"
        else json.dumps(output, indent=2)
    )

    if args.out:
        Path(args.out).write_text(serialized, encoding="utf-8")
        print(f"Written to {args.out}", file=sys.stderr)
    else:
        print(serialized)

    return 1 if total_findings else 0


def _version_text() -> str:
    tools = ", ".join(f"{name} {v}" for name, v in tool_versions().items())
    return f"python-linters {package_version()} ({tools})"


def _reference(args: argparse.Namespace) -> int:
    print(reference_text(args.tool), end="")
    return 0


def _run_config_check(tool: str, config_path: Path) -> bool:
    """Run and print the config check for one tool. Returns whether it's clean."""
    if tool == "ruff":
        check = check_ruff_config(config_path)
        print(format_ruff_report(config_path, check))
    else:
        check = check_ty_config(config_path)
        print(format_ty_report(config_path, check))
    return check.is_clean


def _check_config(args: argparse.Namespace) -> int:
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: {config_path} not found", file=sys.stderr)
        return 2

    try:
        is_clean = _run_config_check(args.tool, config_path)
    except ToolFailedError as e:
        print(str(e), file=sys.stderr)
        return 2

    return 0 if is_clean else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python-linters")
    parser.add_argument(
        "--version",
        action="version",
        version=_version_text(),
        help="print this package's version and its bundled ruff/ty/pymodularity versions",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    lint_parser = subparsers.add_parser(
        "lint", help="run ruff, ty and pymodularity and print one JSON report"
    )
    lint_parser.add_argument("path", nargs="?", default=".")
    lint_parser.add_argument("--out", default=None)
    lint_parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="json (default) or one finding per line, sorted by file then line",
    )
    lint_parser.add_argument(
        "--skip",
        action="append",
        default=[],
        choices=list(TOOL_NAMES),
        help="skip this tool (repeatable); skipping all 4 is an error",
    )
    lint_parser.add_argument(
        "--python",
        dest="ty_python",
        default=None,
        help="forwarded verbatim as ty check's --python",
    )
    lint_parser.add_argument(
        "--extra-search-path",
        dest="ty_extra_search_path",
        action="append",
        default=[],
        help="forwarded verbatim as ty check's --extra-search-path (repeatable)",
    )
    lint_parser.set_defaults(func=_lint, parser=lint_parser)

    reference_parser = subparsers.add_parser(
        "reference", help="print a shipped reference config to stdout"
    )
    reference_parser.add_argument("tool", choices=["ruff", "ty"])
    reference_parser.set_defaults(func=_reference)

    check_config_parser = subparsers.add_parser(
        "check-config", help="compare a config against the pinned tool's current rules"
    )
    check_config_parser.add_argument("tool", choices=["ruff", "ty"])
    check_config_parser.add_argument("config")
    check_config_parser.set_defaults(func=_check_config)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
