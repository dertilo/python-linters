import pathlib

package_dir = str(pathlib.Path(__file__).parent.resolve())

FLAKE8_CONFIG_FILE = f"{package_dir}/.flake8"
RUFF_CONFIG_FILE = f"{package_dir}/ruff.toml"
PYRIGHT_CONFIG_FILE = f"{package_dir}/pyrightconfig.json"

assert pathlib.Path(FLAKE8_CONFIG_FILE).is_file()
assert pathlib.Path(RUFF_CONFIG_FILE).is_file()
assert pathlib.Path(PYRIGHT_CONFIG_FILE).is_file()
