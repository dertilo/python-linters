"""Shared test helpers."""

from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def run_cli(
    *args: str, cwd: Path | None = None, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run this package's own CLI as a subprocess, the pinned-environment way.

    cmd is always a fixed argv list built from this package's own module
    name and caller-supplied args, never shell-interpolated or from
    untrusted input.
    """
    return subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [sys.executable, "-m", "python_linters", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        env=env,
        check=False,
    )
