from python_linters.extending_ruff_toml import create_extended_ruff_toml
from python_linters.getting_to_be_linted_folders import get_folders_to_be_linted

from python_linters.utils import run_cmd_ignore_errors, run_cmd, \
    get_pyproject_dir


def main() -> None:
    """
    $FilePath$ in pycharm
    """
    dirr = get_pyproject_dir()
    folders_to_be_linted = get_folders_to_be_linted(f"{dirr}/pyproject.toml")
    folders = " ".join(folders_to_be_linted)
    extended_ruff_toml = create_extended_ruff_toml(str(dirr))
    run_cmd_ignore_errors(
        f"cd {dirr} && ruff check {folders} --config={extended_ruff_toml} --fix",
    )
    run_cmd(f"cd {dirr} && ruff format {folders} --config={extended_ruff_toml}")




if __name__ == "__main__":
    main()
