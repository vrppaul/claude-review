"""The check CI runs for the code rules no linter here keeps: run as CI runs it, on a file of its own."""

import subprocess
import sys
from pathlib import Path
from textwrap import dedent

CHECK = Path(__file__).parents[2] / "scripts" / "check_code_rules.py"
# What the check exits with: a rule broken, or every rule kept
RULE_BROKEN = 1
ALL_KEPT = 0

NESTED_HELPER = """
    def outer(names: list[str]) -> list[str]:
        def tidy(name: str) -> str:
            return name.strip()

        return [tidy(name) for name in names]
"""

SHORT_NAMES = """
    def total(values: list[int]) -> int:
        s = 0
        for v in values:
            s += v
        return s
"""

KEPT = """
    class Thread:
        def reply(self, body: str, id: str) -> str:
            _, ok = body.partition(id)[0], True
            return str(ok)


    def lengths(names: list[str]) -> list[int]:
        return sorted(map(lambda name: len(name), names))
"""


def _check(tmp_path: Path, source: str) -> subprocess.CompletedProcess[str]:
    checked = tmp_path / "checked.py"
    checked.write_text(dedent(source))
    return subprocess.run([sys.executable, str(CHECK), str(tmp_path)], capture_output=True, text=True, check=False)


def test_a_function_defined_inside_another_is_named_where_it_is(tmp_path: Path) -> None:
    checked = _check(tmp_path, NESTED_HELPER)

    assert checked.returncode == RULE_BROKEN
    assert "checked.py:3: `tidy` is defined inside another function" in checked.stdout


def test_every_name_too_short_to_say_what_it_holds_is_named(tmp_path: Path) -> None:
    checked = _check(tmp_path, SHORT_NAMES)

    assert checked.returncode == RULE_BROKEN
    assert "`s` is too short" in checked.stdout
    assert "`v` is too short" in checked.stdout


def test_methods_lambdas_short_words_and_the_throwaway_pass(tmp_path: Path) -> None:
    checked = _check(tmp_path, KEPT)

    assert (checked.returncode, checked.stdout) == (ALL_KEPT, "")
