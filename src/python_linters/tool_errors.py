"""Shared subprocess-failure handling for every external tool this package runs."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class ToolFailedError(Exception):
    """An external tool exited with a code outside its accepted set.

    Raised at the boundary where the subprocess result is read, so the
    interior (grouping, config comparison, ...) never has to distinguish
    "0 findings" from "the tool crashed and printed nothing".
    """

    def __init__(self, tool: str, stderr: str) -> None:
        self.tool = tool
        self.stderr = stderr
        super().__init__(f"{tool} failed:\n{stderr}")


def run_checked(
    cmd: list[str],
    cwd: Path,
    tool: str,
    ok_codes: tuple[int, ...] = (0,),
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run cmd, raising ToolFailedError unless its exit code is in ok_codes.

    env=None (the default) inherits this process's environment, same as
    subprocess.run's own default. Callers pass an explicit env when the
    inherited one would steer the tool wrong (see run_ty's VIRTUAL_ENV fix).
    """
    result = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]  # cmd is a fixed argv list built by this package, never shell-interpolated or from untrusted input
        cmd, cwd=cwd, capture_output=True, text=True, check=False, env=env
    )
    if result.returncode not in ok_codes:
        raise ToolFailedError(tool, result.stderr)
    return result
