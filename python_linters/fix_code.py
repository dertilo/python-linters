import subprocess
import sys
from pathlib import Path

from python_linters.run_linters import RUFF_CONFIG_FILE, get_folders_to_be_linted


def run_cmd(cmd):
    subprocess.check_call(cmd, stdout=sys.stdout, stderr=sys.stdout, shell=True)


def run_cmd_ignore_errors(cmd):
    subprocess.call(cmd, stdout=sys.stdout, stderr=sys.stdout, shell=True)


def main():
    dirr = Path.cwd()
    folders_to_be_linted = get_folders_to_be_linted("pyproject.toml")
    folders = " ".join(folders_to_be_linted)

    run_cmd(f"cd {dirr} && isort --profile black {folders}")
    run_cmd_ignore_errors(
        f"cd {dirr} && ruff check {folders} --config={RUFF_CONFIG_FILE} --fix",
    )
    run_cmd(f"cd {dirr} && black {folders}")


if __name__ == "__main__":
    main()
