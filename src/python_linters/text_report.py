"""Render a `build_report` result as one line per finding, for a terminal."""

from __future__ import annotations

from python_linters.lint_report import TOOL_NAMES


def format_text_report(report: dict[str, object]) -> str:
    """One line per finding, sorted by file then line, with a totals line last.

    `file:line:col tool/rule message`, matching how ruff and ty print their
    own findings — unlike the JSON report, this is for a human reading a
    terminal, not a script.
    """
    rows: list[tuple[str, int, int, str, str, str]] = []
    for tool in TOOL_NAMES:
        section = report.get(tool)
        if not isinstance(section, dict):
            continue
        for rule, group in section.items():
            rows.extend(
                (
                    location["file"],
                    location["line"],
                    location["col"],
                    tool,
                    rule,
                    location["message"],
                )
                for location in group["locations"]
            )

    rows.sort(key=lambda row: (row[0], row[1]))

    lines = [
        f"{file}:{line}:{col} {tool}/{rule} {message}"
        for file, line, col, tool, rule, message in rows
    ]

    summary_obj = report.get("summary", {})
    summary: dict[str, dict[str, int]] = (
        summary_obj if isinstance(summary_obj, dict) else {}
    )
    totals = " ".join(f"{tool}={data['total']}" for tool, data in summary.items())
    grand_total = sum(data["total"] for data in summary.values())
    totals_line = f"{totals} total={grand_total}" if totals else f"total={grand_total}"

    baseline = report.get("baseline")
    if isinstance(baseline, dict):
        totals_line += f" baseline={baseline['ref']}"

    lines.append(totals_line)

    return "\n".join(lines)
