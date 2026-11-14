# python-linters

Run ruff, ty and pymodularity on a Python project and print one JSON report
grouped by rule, for agents and CI to read.

## Install

As a dev dependency of the project you want to lint:

```
uv add --dev python-linters
```

## Commands

- `uv run python-linters lint [path] [--out FILE] [--format json|text]
  [--skip TOOL]... [--python PATH] [--extra-search-path DIR]...
  [--baseline REF]` — runs
  ruff, `ruff format --check`, ty and pymodularity (default path: `.`) and
  prints the merged report to stdout, or writes it to `FILE` with `--out`.
  - `--format text` prints one line per finding (`file:line:col
    tool/rule message`, sorted by file then line) with a totals line
    last, instead of the default JSON. `--out` writes whichever format
    was chosen.
  - `--skip TOOL` (repeatable; `ruff`, `ruff-format`, `ty`,
    `pymodularity`) drops that tool: it does not run, gets no section and
    no summary entry, and is listed under the report's top-level
    `"skipped"`. Skipping all 4 is a usage error.
  - `--python PATH` and `--extra-search-path DIR` (repeatable) are
    forwarded verbatim to `ty check`'s own `--python`/`--extra-search-path`.
    Needed whenever the project's imports do not resolve from a `.venv`
    under the linted path — e.g. a ROS 2 package that resolves `rclpy`
    and friends from a system interpreter and `/opt/ros/...`.
  - ty looks for a `.venv` at *its own project root* — the directory
    holding the nearest `ty.toml`, or a `pyproject.toml` with a
    `[tool.ty]` section — not at the path you pass to `lint`. A shared
    parent config can point ty's `.venv` search at the wrong directory for
    a sub-package; the report's `"ty-environment"` key (below) shows what
    ty actually resolved.
  - ty ranks `$PYTHONPATH` entries ahead of first-party code. If
    `PYTHONPATH` is set, a stale installed copy on it can shadow the
    project tree being linted and silently report 0 findings; the report
    names it under `"ty-environment"` when set.
  - the report's top-level `"tools"` key names the bundled ruff/ty/
    pymodularity versions; `"ty-environment"` names ty's resolved project
    root and Python environment (absent if `ty` is skipped).
  - `--baseline REF` (a branch, tag, SHA, `HEAD~N`, ...) reports only
    findings that are new since that git ref: it checks the ref out into a
    fresh `git worktree add --detach` scratch directory (never a reused
    one — a stale copy there can carry findings from an earlier run),
    lints the same sub-path there, and drops every current finding whose
    `(file, rule, message)` triple already exists at the baseline. The
    line number is excluded from that triple on purpose: a finding does
    not become "new" just because a line was inserted above it. The
    worktree is removed afterwards regardless of outcome. A ref that
    doesn't resolve, or a `path` outside any git repo, exits 2 with the
    reason on stderr. The report gets a top-level `"baseline": {"ref":
    ..., "sha": ...}`; the summary and exit code count only the new
    findings; `--format text` prints only the new findings plus the
    baseline ref on the totals line. Since a fresh worktree has no
    `.venv` of its own, the baseline's ty run is given `--python`
    explicitly — the current run's resolved `ty-environment` Python
    environment, unless you passed your own `--python` — and the report
    names which one it used under `"baseline"`'s `"ty-python"` key.
    `--skip` and `--extra-search-path` apply to both runs.
  - **File-move artifact in the delta.** The baseline keys findings by
    `(file, rule, message)`. A refactor that moves code from `old/x.py`
    to `new/y.py` reports the entry at `old/x.py` as *gone* and the same
    finding at `new/y.py` as *new* — net delta +1 even though the
    codebase's lint posture is unchanged. Two responses: (a) accept the
    +1 and document the move in the commit message; (b) commit and
    refresh the baseline. Prefer (a) for one-off moves; (b) only when a
    move is large enough to otherwise swamp the real new findings.
- `uv run python-linters --version` — prints this package's version and
  the bundled ruff/ty/pymodularity versions on one line.
- `uv run python-linters reference ruff|ty` — prints this package's shipped
  reference config for the given tool to stdout. The package never writes
  it into your project — copying it into `ruff.toml`/`ty.toml` (or
  `pyproject.toml`) stays with you.
- `uv run python-linters check-config ruff|ty <path/to/config>` — compares
  your copy against the pinned tool's current rule set: rules the tool
  knows that your config omits (untriaged), and rules your config names
  that the tool no longer knows (stale). The report names the version of
  the tool it checked against on its first line.

## Exit codes

- `lint`: 0 clean, 1 findings, 2 any tool failure (named on stderr), a
  usage error (e.g. `--skip` naming all 4 tools), or — with
  `--baseline` — a ref that doesn't resolve or a path outside any git
  repo.
- `check-config`: 0 up to date, 1 untriaged or stale rules found, 2 tool
  failure.
