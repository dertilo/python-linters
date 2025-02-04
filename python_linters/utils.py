import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from python_linters.config_files import PYRIGHT_CONFIG_FILE


def run_cmd(cmd: str) -> int:
    return subprocess.call(cmd, stdout=sys.stdout, stderr=sys.stdout, shell=True)


def run_cmd_ignore_errors(cmd) -> None:
    subprocess.call(cmd, stdout=sys.stdout, stderr=sys.stdout, shell=True)


def find_pyproject_toml(
    path: Path,
) -> Path | None:
    for _ in range(100):
        if path.joinpath("pyproject.toml").is_file():
            return path.joinpath("pyproject.toml")
        else:
            path = path.parent
    return None


def get_pyproject_dir() -> Path:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--filepath",
        type=str,
        default=os.getcwd(),
        help="currently opened file in IDE or current path",
        required=False,
    )
    args = parser.parse_args()
    dirr = find_pyproject_toml(Path(args.filepath)).parent
    return dirr


def prepare_pyrightjson(dirr: str) -> bool:
    pyrightconfig_extension = f"{dirr}/pyrightconfig_extension.json"
    wrote_pyright_json = False
    if Path(pyrightconfig_extension).is_file():
        extended = extend_pyrightjson(PYRIGHT_CONFIG_FILE, pyrightconfig_extension)
        with Path(f"{dirr}/pyrightconfig.json").open("w") as f:
            json.dump(extended, f, indent=4)
        wrote_pyright_json = True
    elif Path(f"{dirr}/pyrightconfig.json").is_file():
        pass
    else:
        shutil.copy(PYRIGHT_CONFIG_FILE, f"{dirr}/pyrightconfig.json")
        wrote_pyright_json = True
    return wrote_pyright_json


import jsonc


def extend_pyrightjson(parent_json: str, child_json: str) -> dict:
    with Path(parent_json).open("r") as f:
        parent = jsonc.load(f)
    with Path(child_json).open("r") as f:
        child = jsonc.load(f)
    for key in parent.keys() | child.keys():
        if key in child:
            parent[key] = child[key]
    return parent
