# python-linters

Run ruff, ty and pymodularity on a Python project and print one JSON report
grouped by rule, for agents and CI to read.

## Install

As a dev dependency of the project you want to lint:

```
uv add --dev python-linters
```

## Commands

- `uv run python-linters lint [path] [--out FILE]` — runs ruff, ty and
  pymodularity (default path: `.`) and prints the merged JSON report to
  stdout, or writes it to `FILE` with `--out`.
- `uv run python-linters reference ruff|ty` — prints this package's shipped
  reference config for the given tool to stdout. The package never writes
  it into your project — copying it into `ruff.toml`/`ty.toml` (or
  `pyproject.toml`) stays with you.
- `uv run python-linters check-config ruff|ty <path/to/config>` — compares
  your copy against the pinned tool's current rule set: rules the tool
  knows that your config omits (untriaged), and rules your config names
  that the tool no longer knows (stale).

## Exit codes

- `lint`: 0 clean, 1 findings, 2 any tool failure (named on stderr).
- `check-config`: 0 up to date, 1 untriaged or stale rules found, 2 tool
  failure.
