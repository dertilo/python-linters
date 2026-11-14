"""Resolved versions of this package and the tools it bundles.

Read from `importlib.metadata`, never from a subprocess call: the versions
are pinned in `pyproject.toml` and installed into the same environment this
package itself runs in, so the installed-distribution metadata already
names exactly what `sys.executable -m <tool>` will run.
"""

from __future__ import annotations

from importlib.metadata import version

TOOL_DISTRIBUTIONS = ("ruff", "ty", "pymodularity")


def package_version() -> str:
    return version("python-linters")


def tool_versions() -> dict[str, str]:
    """Bundled ruff/ty/pymodularity versions, keyed by distribution name."""
    return {name: version(name) for name in TOOL_DISTRIBUTIONS}
