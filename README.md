# python-linters
- bundles flake8, black, isort, ruff into a single poetry-script
- project independent linter configuration (via `ruff.toml`,`.flake8`) -> one config to rule them all
### use-cases:
1. interactively learning python code quality standards via ruff+flake8, see [local development workflow](#2-local-development-workflow-before-pushing-to-ci-pipeline)
2. enforcing minimal quality-standards via a "lint-stage" in a ci-pipeline, see [setup for ci-pipeline](#3-setup-for-ci-pipeline)

## 1. install (via poetry)
1. in `pyproject.toml` add to dependencies
```toml

[tool.poetry.group.dev.dependencies]
python-linters = { version = "<some-version-here>" }
```
2. in your `pyproject.toml` specify the directories that you want to be linted (currently `tests`-dir is added by default)
   a. via `packages`
     ```toml
     packages = [
         { include = "my_package_name" }, 
     ]
     ```
   b. or via `tool.python-linters`
    ```toml
    [tool.python-linters]
    folders_to_be_linted=["my_directory","another_dir/my_sub_package"]
    ```
## 2. local development workflow (before pushing to ci-pipeline)
### enhanced "usability" via VSCODE-Extension
1. git clone this repo
2. install [ruff-extension](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff)
3. add the following to your `settings.json`
```json
    "ruff.lint.args": [
        "--config=<wherever-you-git-cloned-it>/python-linters/python_linters/ruff.toml"
    ],
```
### three scripts/commands that you can run locally
1. `poetry run fixcode` to let black+isort+ruff "auto-fix" your code -> always have a `clean` git-repo before doing this (no uncommitted changes)
   - [example output](#fixcode-example)
1. `poetry run pythonlinter` -> to lint your code
   - [example black is not happy](#pythonlinter-black-is-not-happy) -> if you ran `fixcode` black is guaranteed to be happy!
   - [example ruff is not happy](#pythonlinter-ruff-is-not-happy)
   - [example flake8 is not happy](#pythonlinter-flake8-is-not-happy)
1. `poetry run addnoqa` to let ruff insert rules-violation-comments to your code
   - [example](#addnoqa-example)
```mermaid
flowchart TD
classDef style0 fill:#ffb3ba 
classDef style1 fill:#ffdfba 
classDef style2 fill:#ffffba 
classDef style3 fill:#baffc9 
classDef style4 fill:#bae1ff
op1["start: have a 'clean' repo"]:::style4 --> op2
op2[\"poetry run fixcode\n refactor & git commit"/]:::style1 --> cond9{{"poetry run pythonlinter"}}:::style0
cond9 --> | complains | cond47{{"ruff"}}:::style0
cond47 --> | complains | op51[\"poetry run addnoqa"/]:::style1
op51 -->  sub53[\"refactor your code \nOR\n keep/add noqa-comment"/]:::style1
sub53 --> op2
cond47 --> | is happy | cond58{{"flake8"}}:::style0
cond58 --> | complains | sub53
cond58 --> | is happy | sub66["git commit"]
sub66 -->  sub80
cond9 --> | is happy | sub80["git push"]:::style3
```
- write-operations (changing your code): `poetry run fixcode`, `poerty run addnoqa`, `refactor your code`
- read-only-operations: `poetry run pythonlinter`,`git commit`, `git push`

## 3. setup for ci-pipeline
* if you specified the packages in the `pyproject.toml` and you run just run `poetry run pythonlinter` without any arguments than the `pyproject.toml` is getting parsed and specified packages are getting linted 
```yaml
stages:
  - lint # lint-stage!
  - build
  - test
  - deploy

...

linting:
  stage: lint
  extends: .poetry
  variables:
    DEBIAN_FRONTEND: noninteractive
  script:
    - poetry install --only dev
    - poetry run pythonlinter package_a package_b tests # specify folders to be linted
      ## OR
    - poetry run pythonlinter # to be linted folders are parsed out of the pyproject.toml packages-include section
    


```
## example outputs
### fixcode example
```commandline
cd <somehwere>/whisper-streaming
poetry run fixcode
Fixing <somehwere>/whisper-streaming/whisper_streaming/post_asr_preparations.py
whisper_streaming/faster_whisper_inference/faster_whisper_inferencer.py:231:30: ARG005 Unused lambda argument: `x`
whisper_streaming/faster_whisper_inference/faster_whisper_inferencer.py:234:5: RET503 Missing explicit `return` at the end of function able to return non-`None` value
whisper_streaming/post_asr_preparations.py:113:5: ANN201 Missing return type annotation for public function `remove_empty_segments`
whisper_streaming/post_asr_preparations.py:113:27: ANN001 Missing type annotation for function argument `whisper_output_segments`
Found 5 errors (1 fixed, 4 remaining).
No fixes available (2 hidden fixes can be enabled with the `--unsafe-fixes` option).
reformatted <somehwere>/whisper-streaming/whisper_streaming/post_asr_preparations.py
reformatted <somehwere>/whisper-streaming/whisper_streaming/faster_whisper_inference/faster_whisper_inferencer.py

All done! ✨ 🍰 ✨
2 files reformatted, 20 files left unchanged.
folders_to_be_linted=['whisper_streaming', 'tests']
```

### pythonlinter black is not happy
```commandline
poetry run pythonlinter
linter-order: black->ruff->flake8
folders_tobelinted=['whisper_streaming', 'tests']
running black
would reformat <somehwere>/whisper-streaming/whisper_streaming/post_asr_preparations.py
would reformat <somehwere>/whisper-streaming/whisper_streaming/faster_whisper_inference/faster_whisper_inferencer.py

Oh no! 💥 💔 💥
2 files would be reformatted, 20 files would be left unchanged.
python_linters.run_linters.LinterException: 💩 black is not happy! 💩
```
### pythonlinter ruff is not happy
- complains about
  - an unused argument
  - a missing return statement
  - missing type annotations
```commandline
poetry run pythonlinter
linter-order: black->ruff->flake8

...

running ruff
whisper_streaming/faster_whisper_inference/faster_whisper_inferencer.py:232:29: ARG005 Unused lambda argument: `x`
whisper_streaming/faster_whisper_inference/faster_whisper_inferencer.py:235:5: RET503 Missing explicit `return` at the end of function able to return non-`None` value
whisper_streaming/post_asr_preparations.py:114:5: ANN201 Missing return type annotation for public function `remove_empty_segments`
whisper_streaming/post_asr_preparations.py:114:27: ANN001 Missing type annotation for function argument `whisper_output_segments`
Found 4 errors.
No fixes available (2 hidden fixes can be enabled with the `--unsafe-fixes` option).
python_linters.run_linters.LinterException: 💩 ruff is not happy! 💩
```
### pythonlinter flake8 is not happy
- complains about too many methods in a class and wrong position of a function in a module
```commandline
poetry run pythonlinter
linter-order: black->ruff->flake8
folders_tobelinted=['whisper_streaming', 'tests']
running black
All done! ✨ 🍰 ✨
22 files would be left unchanged.

passed black linter! ✨ 🍰 ✨

running ruff

passed ruff linter! ✨ 🍰 ✨

running flake8
whisper_streaming/faster_whisper_inference/faster_whisper_inferencer.py:111:1: WPS214 Found too many methods: 10 > 9
tests/conftest.py:35:8: NEW100 newspaper style: function is_in_docker_container defined in line 16 should be moved down
python_linters.run_linters.LinterException: 💩 flake8 is not happy! 💩
```
### addnoqa example
- only shows how many noqas it added (`3`) and how many files it left unchanged (`22`)
```commandline
poetry run addnoqa
Added 3 noqa directives.
All done! ✨ 🍰 ✨
22 files would be left unchanged.
folders_tobelinted=['whisper_streaming', 'tests']
addnoqa iteration: 0
```
- it adds noqas like this one:
```python
def foobar(x):
   return "whatever"

from faster_whisper.transcribe import Segment as FasterWhisperSegment  # noqa: E402

```
# IDE integration
## manual vscode integration
- in `.vscode/tasks.json`
```json
{
    // See https://go.microsoft.com/fwlink/?LinkId=733558
    // for the documentation about the tasks.json format
    "version": "2.0.0",
    "tasks": [
        {
            "label": "fixcode",
            "type": "shell",
            "command": "cd $(cd ${fileDirname} && git rev-parse --show-toplevel) && poetry run fixcode"
        },
        {
            "label": "addnoqa",
            "type": "shell",
            "command": "cd $(cd ${fileDirname} && git rev-parse --show-toplevel) && poetry run addnoqa"
        },
        {
            "label": "pythonlinter",
            "type": "shell",
            "command": "cd $(cd ${fileDirname} && git rev-parse --show-toplevel) && poetry run pythonlinter"
        }
    ]
}
```
## manual pycharm integration
![pycharm_settings.png](pycharm_settings.png)
## alternatives
- https://github.com/astral-sh/ruff-vscode
- https://plugins.jetbrains.com/plugin/20574-ruff