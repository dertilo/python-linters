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
from python_linters.lint_report import build_report
from python_linters.reference_files import reference_text
from python_linters.tool_errors import ToolFailedError


def _lint(args: argparse.Namespace) -> int:
    project_path = Path(args.path).resolve()
    if not project_path.exists():
        print(f"Error: {project_path} does not exist", file=sys.stderr)
        return 2

    try:
        output, total_findings = build_report(project_path)
    except ToolFailedError as e:
        print(str(e), file=sys.stderr)
        return 2

    serialized = json.dumps(output, indent=2)

    if args.out:
        Path(args.out).write_text(serialized, encoding="utf-8")
        print(f"Written to {args.out}", file=sys.stderr)
    else:
        print(serialized)

    return 1 if total_findings else 0


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
    subparsers = parser.add_subparsers(dest="command", required=True)

    lint_parser = subparsers.add_parser(
        "lint", help="run ruff, ty and pymodularity and print one JSON report"
    )
    lint_parser.add_argument("path", nargs="?", default=".")
    lint_parser.add_argument("--out", default=None)
    lint_parser.set_defaults(func=_lint)

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
