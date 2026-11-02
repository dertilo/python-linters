"""Compare a ruff or ty config against the pinned tool's current rule set.

Ported from check_ruff_rules.py and check_ty_rules.py (quality-and-security-tools
howtos). Both tools run as `sys.executable -m <tool>` — the python-linters
environment's own pinned version, same resolution as lint_report.py — so
check_ty_rules.py's `--ty-version` flag (for checking a reference file
against a version the howto repo doesn't pin) is dropped: python-linters
always pins its own ty.
"""

from __future__ import annotations

import json
import re
import string
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from python_linters.tool_errors import run_checked

# ── ruff ──────────────────────────────────────────────────────────────────


@dataclass
class RuffConfigCheck:
    version: str
    category_count: int
    selected_count: int
    commented_count: int
    new_categories: list[tuple[str, str]]
    removed: list[str]
    untriaged_codeless: list[str]
    untriaged_preview: list[tuple[str, str]]

    @property
    def is_clean(self) -> bool:
        return not (
            self.new_categories
            or self.removed
            or self.untriaged_codeless
            or self.untriaged_preview
        )


def _get_ruff_rules() -> list[dict[str, Any]]:
    result = run_checked(
        [sys.executable, "-m", "ruff", "rule", "--all", "--output-format", "json"],
        Path.cwd(),
        "ruff",
    )
    return json.loads(result.stdout)


def _get_ruff_version() -> str:
    result = run_checked([sys.executable, "-m", "ruff", "version"], Path.cwd(), "ruff")
    return result.stdout.strip()


def _get_ruff_categories(rules: list[dict[str, Any]]) -> dict[str, str]:
    """All rule categories (prefix -> one representative linter name, for display)."""
    categories: dict[str, str] = {}
    for r in rules:
        code = r["code"]
        if code is None:
            continue
        prefix = code.rstrip(string.digits)
        if prefix not in categories:
            categories[prefix] = r["linter"]
    return categories


def _get_category_linters(rules: list[dict[str, Any]]) -> dict[str, set[str]]:
    """Every rule category (prefix) -> the full set of linters under it.

    A single rstrip(digits) prefix can hold rules from more than one ruff
    linter, e.g. "C" holds both flake8-comprehensions and mccabe, "T" holds
    both flake8-debugger and flake8-print. Those prefixes behave like "PL"
    (which spans PLC/PLE/PLR/PLW): selecting them selects several linters
    at once. A prefix with exactly one linter does not: selecting "N"
    (pep8-naming) must not be read as covering "NPY" (NumPy-specific rules)
    just because "NPY" starts with "N".
    """
    category_linters: dict[str, set[str]] = {}
    for r in rules:
        code = r["code"]
        if code is None:
            continue
        prefix = code.rstrip(string.digits)
        category_linters.setdefault(prefix, set()).add(r["linter"])
    return category_linters


def _get_codeless_rules(rules: list[dict[str, Any]]) -> list[str]:
    """Names of rules without a code (`"code": null`, e.g. pytest-fixture-autouse).

    No prefix selects them, so only a name in select (or `ALL`) enables them.
    """
    return sorted(r["name"] for r in rules if r["code"] is None)


def _parse_toml_lint(toml_path: Path) -> dict[str, Any]:
    """Read the lint table from ruff.toml or pyproject.toml.

    tomllib, not a regex: a `]` inside a comment (e.g. `[lint.flake8-tidy-imports]`)
    ended a regex-matched array early.
    """
    data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    ruff = data.get("tool", {}).get("ruff", data)
    lint = dict(ruff.get("lint", {}))
    lint.setdefault("select", ruff.get("select", []))
    lint.setdefault("ignore", ruff.get("ignore", []))
    return lint


def _parse_toml_comments(toml_path: Path) -> set[str]:
    """Find excluded categories, rule prefixes and code-less rule names.

    Expects lines like: # excluded    "ERA",   # eradicate
    A line may list several entries before its reason: # excluded "E11", "E2",  # why
    """
    content = toml_path.read_text(encoding="utf-8")
    entries: set[str] = set()
    for listed in re.findall(r"^#\s*excluded\s+(.*)$", content, re.MULTILINE):
        entries.update(re.findall(r'"([^"]+)"', listed.split("#", 1)[0]))
    return entries


def _covers(
    selector: str,
    category: str,
    category_linters: dict[str, set[str]],
    meta_prefixes: set[str],
) -> bool:
    """True iff a selected/excluded `selector` covers rule `category`.

    Ruff's own prefix resolution: a selector covers only categories of its
    own linter(s). Equal is always covered. A strict extension is covered
    only if `selector` is a meta prefix (spans several linters, e.g. "PL",
    "C", "T") or `selector` and `category` share the same linter set.
    """
    if category == selector:
        return True
    if not category.startswith(selector):
        return False
    if selector in meta_prefixes:
        return True
    return category_linters.get(selector) == category_linters.get(category)


def _covers_rule(
    selector: str,
    code: str,
    linter: str,
    rules: list[dict[str, Any]],
    meta_prefixes: set[str],
) -> bool:
    """Same rule as `_covers`, for one concrete rule code rather than a category.

    `code` (e.g. "C416") and partial selectors like "C90" are not category
    keys (only the blended rstrip prefix "C" is), so `selector`'s own
    linter set is computed straight from the rules it actually matches.
    """
    if code == selector:
        return True
    if not code.startswith(selector):
        return False
    if selector in meta_prefixes:
        return True
    selector_linters = {
        r["linter"] for r in rules if r["code"] and r["code"].startswith(selector)
    }
    return selector_linters == {linter}


def _get_untriaged_preview(
    rules: list[dict[str, Any]],
    selected: set[str],
    ignored: set[str],
    excluded: set[str],
) -> list[tuple[str, str]]:
    """Preview rules a selected category contains but nobody triaged.

    Triaged means: named (or coded) in select or ignore, or covered by an
    `# excluded` prefix.
    """
    rule_names = {r["name"] for r in rules}
    category_selects = selected - rule_names
    named = selected | ignored
    untriaged = []
    for r in rules:
        code, name = r["code"], r["name"]
        if not r.get("preview") or code is None or name is None:
            continue
        if not any(code.startswith(p) for p in category_selects):
            continue
        if name in named or code in named:
            continue
        if any(code.startswith(p) for p in excluded):
            continue
        untriaged.append((code, name))
    return sorted(untriaged)


def _get_new_categories(
    rules: list[dict[str, Any]],
    categories: dict[str, str],
    category_linters: dict[str, set[str]],
    known: set[str],
    meta_prefixes: set[str],
) -> list[tuple[str, str]]:
    """Categories no selector in `known` triages.

    A multi-linter prefix (e.g. "C" = flake8-comprehensions + mccabe) can be
    fully triaged by several single-linter selectors together (e.g. "C4" +
    "C90"), without any selector covering the blended prefix itself. So a
    category only stays "new" if some of its own rules are left uncovered
    by every selector in known, checked rule by rule.
    """
    new_categories = []
    for prefix, linter in sorted(categories.items()):
        if any(_covers(k, prefix, category_linters, meta_prefixes) for k in known):
            continue
        prefix_rules = [
            r for r in rules if r["code"] and r["code"].rstrip(string.digits) == prefix
        ]
        if all(
            any(
                _covers_rule(k, r["code"], r["linter"], rules, meta_prefixes)
                for k in known
            )
            for r in prefix_rules
        ):
            continue
        new_categories.append((prefix, linter))
    return new_categories


def _get_removed(rules: list[dict[str, Any]], selected: set[str]) -> list[str]:
    """Select entries that are neither a rule name nor a prefix of any real rule code.

    A misspelt name lands here: ruff itself only warns.
    """
    rule_names = {r["name"] for r in rules}
    rule_codes = [r["code"] for r in rules if r["code"] is not None]
    return [
        code
        for code in sorted(selected)
        if code not in rule_names and not any(c.startswith(code) for c in rule_codes)
    ]


def check_ruff_config(toml_path: Path) -> RuffConfigCheck:
    version = _get_ruff_version()
    rules = _get_ruff_rules()
    categories = _get_ruff_categories(rules)
    category_linters = _get_category_linters(rules)
    lint = _parse_toml_lint(toml_path)
    selected = set(lint["select"])
    commented = _parse_toml_comments(toml_path)

    known = selected | commented
    meta_prefixes = {"PL"} | {
        p for p, linters in category_linters.items() if len(linters) > 1
    }

    new_categories = _get_new_categories(
        rules, categories, category_linters, known, meta_prefixes
    )
    removed = _get_removed(rules, selected)

    untriaged_codeless = [n for n in _get_codeless_rules(rules) if n not in known]

    untriaged_preview = []
    if lint.get("explicit-preview-rules"):
        untriaged_preview = _get_untriaged_preview(
            rules, selected, set(lint["ignore"]), commented
        )

    return RuffConfigCheck(
        version=version,
        category_count=len(categories),
        selected_count=len(selected),
        commented_count=len(commented),
        new_categories=new_categories,
        removed=removed,
        untriaged_codeless=untriaged_codeless,
        untriaged_preview=untriaged_preview,
    )


def format_ruff_report(toml_path: Path, check: RuffConfigCheck) -> str:
    lines = [
        f"Ruff version: {check.version}",
        f"Config: {toml_path}",
        f"Categories in ruff: {check.category_count}",
        f"Selected in config: {check.selected_count}",
        f"Commented/excluded: {check.commented_count}",
        "",
    ]

    if check.new_categories:
        lines.append(f"NEW categories not yet triaged ({len(check.new_categories)}):")
        lines.append("  Add to select or comment out with '# excluded' in ruff.toml:\n")
        lines.extend(
            f'    "{prefix}",\t# {linter}' for prefix, linter in check.new_categories
        )
        lines.append("")

    if check.removed:
        lines.append(
            f"REMOVED/RENAMED categories still in select ({len(check.removed)}):"
        )
        lines.extend(f"    {code}" for code in check.removed)
        lines.append("")

    if check.untriaged_codeless:
        lines.append(
            f"Code-less rules not yet triaged ({len(check.untriaged_codeless)}):"
        )
        lines.append(
            "  Add to select by name or comment out with '# excluded' in ruff.toml:\n"
        )
        lines.extend(f'    "{name}",' for name in check.untriaged_codeless)
        lines.append("")

    if check.untriaged_preview:
        lines.append(f"Preview rules not yet triaged ({len(check.untriaged_preview)}):")
        lines.append(
            "  Add to select by name or cover with an '# excluded' line in ruff.toml:\n"
        )
        lines.extend(
            f'    "{name}",\t# {code}' for code, name in check.untriaged_preview
        )
        lines.append("")

    if check.is_clean:
        lines.append("All categories accounted for. Config is up to date.")

    return "\n".join(lines)


# ── ty ────────────────────────────────────────────────────────────────────


@dataclass
class TyConfigCheck:
    version: str
    rule_count: int
    named_count: int
    untriaged: list[str]
    default_levels: dict[str, str]
    stale: list[str]

    @property
    def is_clean(self) -> bool:
        return not (self.untriaged or self.stale)


def _get_ty_rules() -> dict[str, str]:
    """Ask ty for every rule it knows (name -> default level)."""
    result = run_checked(
        [sys.executable, "-m", "ty", "explain", "rule", "--output-format", "json"],
        Path.cwd(),
        "ty",
    )
    rules = json.loads(result.stdout)
    return {r["name"]: r["default_level"] for r in rules}


def _get_ty_version() -> str:
    result = run_checked([sys.executable, "-m", "ty", "--version"], Path.cwd(), "ty")
    return result.stdout.strip()


def _parse_toml_rules(config_path: Path) -> set[str]:
    """Read the rule table from ty.toml (`[rules]`) or pyproject.toml (`[tool.ty.rules]`).

    tomllib, not a regex, for the same reason check_ruff_config uses it:
    a rule name could appear inside a comment without this breaking.
    """
    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    if "tool" in data:
        rules = data.get("tool", {}).get("ty", {}).get("rules", {})
    else:
        rules = data.get("rules", {})
    return set(rules.keys())


def check_ty_config(config_path: Path) -> TyConfigCheck:
    version = _get_ty_version()
    rules = _get_ty_rules()
    named = _parse_toml_rules(config_path)

    known = set(rules)
    untriaged = sorted(known - named)
    stale = sorted(named - known)

    return TyConfigCheck(
        version=version,
        rule_count=len(known),
        named_count=len(named),
        untriaged=untriaged,
        default_levels=rules,
        stale=stale,
    )


def format_ty_report(config_path: Path, check: TyConfigCheck) -> str:
    lines = [
        f"ty version: {check.version}",
        f"Config: {config_path}",
        f"Rules in ty: {check.rule_count}",
        f"Named in config: {check.named_count}",
        "",
    ]

    if check.untriaged:
        lines.append(
            f"UNTRIAGED rules ty knows that the config omits ({len(check.untriaged)}):"
        )
        lines.extend(
            f'    {name} = "???"  # default: {check.default_levels[name]}'
            for name in check.untriaged
        )
        lines.append("")

    if check.stale:
        lines.append(
            f"STALE rules named in config that ty no longer knows ({len(check.stale)}):"
        )
        lines.extend(f"    {name}" for name in check.stale)
        lines.append("")

    if check.is_clean:
        lines.append("All rules accounted for. Config is up to date.")

    return "\n".join(lines)
