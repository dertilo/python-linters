import re

if __name__ == "__main__":
    code2desc = []
    pattern = re.compile(r"^\w{1,5}\d{1,3}\s\t")

    def parse_line(line: str):
        code, short_expl, long_expl, _category = (
            l.strip(" ") for l in line.split("\t")
        )
        return code, f"{short_expl}: {long_expl}"

    with open("python_linter_configs/ruff_rules.txt") as f:
        code_desc = (
            parse_line(l) for l in f.readlines() if pattern.match(l) is not None
        )
        code2desc = dict(code_desc)
    print(code2desc)
