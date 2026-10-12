"""The check CI runs for the code rules no linter here keeps: run as CI runs it, on a file of its own."""

import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest

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


# Ways of naming a model's fields in text, each in a function of its own, and what the check says of each
COPIED_WITH_AN_UPDATE = """
    def moved(anchor: Anchor, line: int) -> Anchor:
        return anchor.model_copy(update={"line": line})
"""
SPREAD_INTO_A_MAPPING = """
    def moved(anchor: Anchor, line: int) -> Anchor:
        return Anchor.model_validate({**anchor.model_dump(), "line": line})
"""
SPREAD_INTO_A_CALL = """
    def told(step: Step, piece: Piece) -> ToldStep:
        return ToldStep(**dict(step), piece=piece)
"""
MERGED_WITH_ANOTHER = """
    def changed(record: Record, change: Change) -> Record:
        return Record.model_validate(record.model_dump() | change.model_dump())
"""
FIELDS_NAMED_IN_TEXT = [
    (COPIED_WITH_AN_UPDATE, "checked.py:3: `model_copy(update=…)` names a model's fields in text"),
    (SPREAD_INTO_A_MAPPING, "checked.py:3: a model written out as a mapping is spread with `**`"),
    (SPREAD_INTO_A_CALL, "checked.py:3: a model written out as a mapping is spread with `**`"),
    (MERGED_WITH_ANOTHER, "checked.py:3: a model written out as a mapping is merged with `|`"),
]
WAYS_OF_NAMING_THEM = ["copied-with-an-update", "spread-into-a-mapping", "spread-into-a-call", "merged-with-another"]

# What names no model's field in text: a model made by its constructor, a copy with nothing changed, a model
# written out whole for whoever reads it, and mappings that never were models, spread and merged
MODELS_MADE_AND_MAPPINGS_MERGED = """
    class Anchor(BaseModel):
        line: int

        def moved_to(self, line: int) -> Anchor:
            return Anchor(line=line)


    def copied(anchor: Anchor) -> Anchor:
        return anchor.model_copy()


    def answered(refusal: Refusal) -> Response:
        return Response(content=refusal.model_dump())


    def described(replies: dict[int, str], refusals: dict[int, str]) -> dict[int, str]:
        return {**replies, **refusals}


    def chosen(defaults: dict[str, str], choices: dict[str, str]) -> dict[str, str]:
        return defaults | choices


    def rendered(options: dict[str, str]) -> str:
        return render(**options)
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


@pytest.mark.parametrize(("source", "said"), FIELDS_NAMED_IN_TEXT, ids=WAYS_OF_NAMING_THEM)
def test_a_models_fields_named_in_text_are_named_where_they_are(tmp_path: Path, source: str, said: str) -> None:
    """A copy with an update, a model spread or merged as a mapping: names no type checker reads."""
    checked = _check(tmp_path, source)

    assert checked.returncode == RULE_BROKEN
    assert said in checked.stdout


def test_a_model_made_by_its_constructor_and_mappings_that_were_never_models_pass(tmp_path: Path) -> None:
    checked = _check(tmp_path, MODELS_MADE_AND_MAPPINGS_MERGED)

    assert (checked.returncode, checked.stdout) == (ALL_KEPT, "")
