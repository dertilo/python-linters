import sys
from pathlib import Path

from python_linters.extending_ruff_toml import create_extended_ruff_toml
from python_linters.getting_to_be_linted_folders import get_folders_to_be_linted
from python_linters.utils import run_cmd, get_pyproject_dir, prepare_pyrightjson


class LinterException(Exception):
    def __init__(self, linter_name: str):
        sys.tracebacklimit = -1  # to disable traceback
        super().__init__(f"💩 {linter_name} is not happy! 💩")




def main() -> None:
    dirr = get_pyproject_dir()
    folders_tobelinted = get_folders_to_be_linted(f"{dirr}/pyproject.toml")
    wrote_pyright_json = prepare_pyrightjson(str(dirr))

    NAME2LINTER = {
        "ruff-format": lambda folders_tobelinted: f"cd {dirr} && ruff format --check {' '.join(folders_tobelinted)} --config={create_extended_ruff_toml(str(dirr))}",
        "ruff": lambda folders_tobelinted: f"cd {dirr} && ruff check {' '.join(folders_tobelinted)} --config={create_extended_ruff_toml(str(dirr))}",
        "basedpyright": lambda folders_tobelinted: f"cd {dirr} && basedpyright {' '.join(folders_tobelinted)} --gitlabcodequality report.json --level $(cat pyrightlevel.txt 2>/dev/null || echo 'error')",
        # most flake8 linters are already included in ruff
        # the news-paper-style function ordering rule is currently only enforced by a flake8 plugin but its not that important
        # "flake8": lambda folders_tobelinted: f"poetry run flake8 --config={FLAKE8_CONFIG_FILE} {' '.join(folders_tobelinted)}",
    }

    print(f"linter-order: {'->'.join(NAME2LINTER.keys())}")
    sys.stdout.flush()
    try:
        for linter_name, linter_cmd_factory in NAME2LINTER.items():
            print(f"running {linter_name}")
            sys.stdout.flush()

            if run_cmd(linter_cmd_factory(folders_tobelinted)) != 0:
                raise LinterException(linter_name)
            print(f"\npassed {linter_name} linter! ✨ 🍰 ✨\n")
    finally:
        if wrote_pyright_json:
            Path(f"{dirr}/pyrightconfig.json").unlink()




if __name__ == "__main__":
    main()
