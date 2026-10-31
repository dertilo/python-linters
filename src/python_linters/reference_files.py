"""Print a shipped reference config via importlib.resources.

The package never writes a reference into the linted project — the user
copies it, per the brief's "copying stays with the user".
"""

from __future__ import annotations

from importlib import resources

_REFERENCE_FILENAMES = {
    "ruff": "ruff.reference.toml",
    "ty": "ty.reference.toml",
}


def reference_text(tool: str) -> str:
    """Return a shipped reference config's full text.

    Raises KeyError for a tool with no shipped reference — the CLI turns
    that into argparse's own `choices=` error instead of calling this with
    an unknown tool.
    """
    filename = _REFERENCE_FILENAMES[tool]
    return resources.files("python_linters.references").joinpath(filename).read_text()
