from collections.abc import Iterator
from pathlib import Path

from python_linters.config_files import RUFF_CONFIG_FILE


def create_extended_ruff_toml() -> str:
    ruff_extension_file = Path("ruff_extension.toml")

    if ruff_extension_file.is_file():
        fingerprint = f"{ruff_extension_file.stat().st_size}-{ruff_extension_file.stat().st_mtime}"
        extended_ruff_toml_file = f"extended_ruff-{fingerprint}.toml"
        if not Path(extended_ruff_toml_file).is_file():
            print(f"extending {RUFF_CONFIG_FILE} with {ruff_extension_file=}")
            with Path(extended_ruff_toml_file).open("w", encoding="locale") as f:
                lines = [
                    f'extend = "{RUFF_CONFIG_FILE}"',
                    *list(_read_lines(ruff_extension_file)),
                ]
                for l in lines:
                    f.write(f"{l}\n")
        else:
            print(f"using {extended_ruff_toml_file}")
    else:
        extended_ruff_toml_file = RUFF_CONFIG_FILE
    return extended_ruff_toml_file


def _read_lines(
    file: Path,
    encoding: str = "utf-8",
) -> Iterator[str]:
    with file.open(mode="rb") as f:
        for raw_line in f:
            line = raw_line.decode(encoding)
            line = line.replace("\n", "").replace("\r", "")
            yield line
