import subprocess
import sys
from pathlib import Path

from python_linters.extending_ruff_toml import create_extended_ruff_toml
from python_linters.getting_to_be_linted_folders import get_folders_to_be_linted


def run_cmd(cmd) -> None:
    subprocess.check_call(cmd, stdout=sys.stdout, stderr=sys.stdout, shell=True)


def run_cmd_ignore_errors(cmd) -> None:
    subprocess.call(cmd, stdout=sys.stdout, stderr=sys.stdout, shell=True)


def main() -> None:
    dirr = Path.cwd()
    folders_to_be_linted = get_folders_to_be_linted("pyproject.toml")
    folders = " ".join(folders_to_be_linted)

    run_cmd_ignore_errors(
        f"cd {dirr} && ruff check {folders} --config={create_extended_ruff_toml()} --fix",
    )
    run_cmd(f"cd {dirr} && ruff format {folders}")


if __name__ == "__main__":
    main()
