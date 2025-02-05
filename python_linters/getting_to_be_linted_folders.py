import pathlib
import sys

import toml


class PackagesOrFoldersToBeLintedAreNotProperlyDefined(Exception):  # noqa: N818
    def __init__(self) -> None:
        sys.tracebacklimit = -1
        msg = """in your pyproject.toml specify the directories that you want to be linted
a. via packages

packages = [
    { include = \"my_package_name\" },
]

b. or via tool.python-linters

[tool.python-linters]
folders_to_be_linted=["my_directory","another_dir/my_sub_package"]"""
        super().__init__(msg)


def get_folders_to_be_linted(pyproject_toml: str) -> list[str]:
    if not pathlib.Path(pyproject_toml).is_file():
        msg = f"pyproject.toml not found in {pathlib.Path.cwd()}\nplease run this script from the root of your project"
        raise FileNotFoundError(
            msg,
        )

    with open(pyproject_toml, encoding="locale") as f:
        t = toml.load(f)
        folders = (
            t.get("tool", {})
            .get("python-linters", {})
            .get("folders_to_be_linted", None)
        )
        if folders is None:
            folders = ["./"]
            # raise PackagesOrFoldersToBeLintedAreNotProperlyDefined
    print(f"found following {folders=}")
    return folders
