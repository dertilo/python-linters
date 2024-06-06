import os

from python_linters.extending_ruff_toml import create_extended_ruff_toml
from python_linters.getting_to_be_linted_folders import get_folders_to_be_linted
from python_linters.run_linters import run_cmd


def main() -> None:
    """
    expects to run from $ContentRoot$
    """
    folders_tobelinted = get_folders_to_be_linted("pyproject.toml")
    BIG_NUMBER = 9
    for k in range(
        BIG_NUMBER,
    ):  # theoretically could be necessary to run this loop as long as code changes!
        print(f"addnoqa iteration: {k}")
        run_cmd(
            f"ruff check {' '.join(folders_tobelinted)} --config={create_extended_ruff_toml()} --add-noqa",
        )
        try:
            run_cmd(f"ruff format --check {' '.join(folders_tobelinted)}")
            break
        except Exception:
            run_cmd(f"ruff format {' '.join(folders_tobelinted)}")
            run_cmd(f"fixcode {os.getcwd()}")


if __name__ == "__main__":
    main()
