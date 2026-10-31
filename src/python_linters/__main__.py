import sys

from python_linters.cli_commands import main as _cli_main


def main() -> None:
    sys.exit(_cli_main())


if __name__ == "__main__":
    main()
