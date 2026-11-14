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
  [--skip TOOL]... [--python PATH] [--extra-search-path DIR]...` — runs
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

- `lint`: 0 clean, 1 findings, 2 any tool failure (named on stderr) or a
  usage error (e.g. `--skip` naming all 4 tools).
- `check-config`: 0 up to date, 1 untriaged or stale rules found, 2 tool
  failure.
