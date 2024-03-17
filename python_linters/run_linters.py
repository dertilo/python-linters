import pathlib
import subprocess
import sys

import toml


# TODO: one could brute-force search all files and replace codes, but is there a more elegant way?
# def replace_noqa_code():
#     >> > import re
#     >> > l = {'NORTH': 'N', 'SOUTH': 'S', 'EAST': 'E', 'WEST': 'W'}
#     >> > pattern = '|'.join(sorted(re.escape(k) for k in l))
#     >> > address = "123 north anywhere street"
#     >> > re.sub(pattern, lambda m: l.get(m.group(0).upper()), address,
#                 flags=re.IGNORECASE)
#     '123 N anywhere street'
#     >> >
#
def run_cmd(cmd: str) -> int:
    return subprocess.call(cmd, stdout=sys.stdout, stderr=sys.stdout, shell=True)


package_dir = str(pathlib.Path(__file__).parent.resolve())

FLAKE8_CONFIG_FILE = f"{package_dir}/.flake8"
RUFF_CONFIG_FILE = f"{package_dir}/ruff.toml"
assert pathlib.Path(FLAKE8_CONFIG_FILE).is_file()
assert pathlib.Path(RUFF_CONFIG_FILE).is_file()

RUFF_ARGS = ["--fix", "--add-noqa"]


class PackagesOrFoldersToBeLintedAreNotProperlyDefined(Exception):  # noqa: N818
    def __init__(self) -> None:
        sys.tracebacklimit = -1
        msg = """in your pyproject.toml specify the directories that you want to be linted
a. via packages

packages = [
    { include = \"my_package_name\" },
]

b. or via tool.python-linter

[tool.python-linter]
folders_to_be_linted=["my_directory","another_dir/my_sub_package"]"""
        super().__init__(msg)


def get_folders_to_be_linted(pyproject_toml: str) -> list[str]:
    if not pathlib.Path(pyproject_toml).is_file():
        raise FileNotFoundError(
            f"pyproject.toml not found in {pathlib.Path.cwd()}\nplease run this script from the root of your project",
        )

    with open(pyproject_toml) as f:
        t = toml.load(f)
        folders = (
            t.get("tool", {}).get("python-linter", {}).get("folders_to_be_linted", None)
        )
        if (
            folders is None
            and (packages := t.get("tool", {}).get("poetry", {}).get("packages", None))
            is not None
        ):
            folders = [p["include"] for p in packages]
            if pathlib.Path(f"{pathlib.Path(pyproject_toml).parent}/tests").is_dir():
                folders += ["tests"]

        if folders is None:
            raise PackagesOrFoldersToBeLintedAreNotProperlyDefined
    assert len(folders) > 0
    print(f"found following {folders=}")
    return folders


class LinterException(Exception):
    def __init__(self, linter_name: str):
        sys.tracebacklimit = -1  # to disable traceback
        super().__init__(f"💩 {linter_name} is not happy! 💩")


NAME2LINTER = {
    "black": lambda folders_tobelinted: f"black --check {' '.join(folders_tobelinted)}",
    "ruff": lambda folders_tobelinted: f"poetry run ruff check {' '.join(folders_tobelinted)} --config={RUFF_CONFIG_FILE}",
    "flake8": lambda folders_tobelinted: f"poetry run flake8 --config={FLAKE8_CONFIG_FILE} {' '.join(folders_tobelinted)}",
}


def main():
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
