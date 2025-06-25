from collections.abc import Iterator
from pathlib import Path

from python_linters.config_files import RUFF_CONFIG_FILE


def create_extended_ruff_toml(package_root:str) -> str:
    ruff_extension_file = Path(f"{package_root}/ruff_extension.toml")
    ruff_toml_file = Path(f"{package_root}/ruff.toml")
    if ruff_toml_file.is_file():
        ruff_config_file = str(ruff_toml_file)
    else:
        ruff_config_file = RUFF_CONFIG_FILE

    print(f"using {ruff_config_file=}")
    if ruff_extension_file.is_file():
        extended_ruff_toml_file = f"{package_root}/extended_ruff.toml"
        if not Path(extended_ruff_toml_file).is_file():
            print(f"extending {ruff_config_file} with {ruff_extension_file=}")
            with Path(extended_ruff_toml_file).open("w", encoding="locale") as f:
                lines = [
                    f'extend = "{ruff_config_file}"',
                    *list(_read_lines(ruff_extension_file)),
                ]
                for l in lines:
                    f.write(f"{l}\n")
        else:
            print(f"using {extended_ruff_toml_file}")
    else:
        extended_ruff_toml_file = ruff_config_file
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
