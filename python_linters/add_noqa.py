import os

from python_linters.run_linters import (
    RUFF_CONFIG_FILE,
    get_folders_to_be_linted,
    run_cmd,
)


def main():
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
            f"poetry run ruff check {' '.join(folders_tobelinted)} --config={RUFF_CONFIG_FILE} --add-noqa",
        )
        try:
            run_cmd(f"black --check {' '.join(folders_tobelinted)}")
            break
        except Exception:
            run_cmd(f"black {' '.join(folders_tobelinted)}")
            run_cmd(f"poetry run fixcode {os.getcwd()}")


if __name__ == "__main__":
    main()
