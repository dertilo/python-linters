import subprocess
import sys

from python_linters.config_files import PYRIGHT_CONFIG_FILE
from python_linters.extending_ruff_toml import create_extended_ruff_toml
from python_linters.getting_to_be_linted_folders import get_folders_to_be_linted


def run_cmd(cmd: str) -> int:
    return subprocess.call(cmd, stdout=sys.stdout, stderr=sys.stdout, shell=True)


class LinterException(Exception):
    def __init__(self, linter_name: str):
        sys.tracebacklimit = -1  # to disable traceback
        super().__init__(f"💩 {linter_name} is not happy! 💩")


NAME2LINTER = {
    "ruff-format": lambda folders_tobelinted: f"ruff format --check {' '.join(folders_tobelinted)}",
    "ruff": lambda folders_tobelinted: f"poetry run ruff check {' '.join(folders_tobelinted)} --config={create_extended_ruff_toml()}",
    "basedpyright": lambda folders_tobelinted: f"cp -n {PYRIGHT_CONFIG_FILE} ./ && poetry run basedpyright {' '.join(folders_tobelinted)} --gitlabcodequality report.json --level $(cat pyrightlevel.txt 2>/dev/null || echo 'warning')",
    # most flake8 linters are already included in ruff
    # the news-paper-style function ordering rule is currently only enforced by a flake8 plugin but its not that important
    # "flake8": lambda folders_tobelinted: f"poetry run flake8 --config={FLAKE8_CONFIG_FILE} {' '.join(folders_tobelinted)}",
}


def main() -> None:
    folders_tobelinted = get_folders_to_be_linted("pyproject.toml")
    print(f"linter-order: {'->'.join(NAME2LINTER.keys())}")
    sys.stdout.flush()

    for linter_name, linter_cmd_factory in NAME2LINTER.items():
        print(f"running {linter_name}")
        sys.stdout.flush()

        if run_cmd(linter_cmd_factory(folders_tobelinted)) != 0:
            raise LinterException(linter_name)
        print(f"\npassed {linter_name} linter! ✨ 🍰 ✨\n")


if __name__ == "__main__":
    main()
