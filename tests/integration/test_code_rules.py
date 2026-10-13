"""The check CI runs for the code rules no linter here keeps: run as CI runs it, on a file of its own."""

import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest
from pydantic import BaseModel, ConfigDict

CHECK = Path(__file__).parents[2] / "scripts" / "check_code_rules.py"
# What the check exits with: a rule broken, or every rule kept
RULE_BROKEN = 1
ALL_KEPT = 0

# A file that starts two processes itself, what a script that does so is told, and the files that may
STARTS_PROCESSES = """
    import asyncio
    from asyncio import create_subprocess_shell


    async def listed(directory: str) -> None:
        await asyncio.create_subprocess_exec("ls", directory)
        await create_subprocess_shell("ls")
"""
A_SCRIPT_STARTS_NONE = "starts a process: a script starts one through `scripts/commands.py`, which stops what it starts"
MAY_START_PROCESSES = ["scripts/commands.py", "src/package/repository.py"]

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


class FieldsByName(BaseModel):
    """One way of taking a model apart by the names of its fields, or of putting one together from them."""

    model_config = ConfigDict(frozen=True)

    what: str
    source: str
    said: str


FIELDS_BY_NAME = [
    FieldsByName(
        what="a copy with fields updated",
        source="""
            def moved(anchor: Anchor, line: int) -> Anchor:
                return anchor.model_copy(update={"line": line})
        """,
        said="checked.py:3: `model_copy` copies a model past its constructor",
    ),
    FieldsByName(
        what="a model built unchecked",
        source="""
            def moved(line: int) -> Anchor:
                return Anchor.model_construct(line=line)
        """,
        said="checked.py:3: `model_construct` builds a model unchecked",
    ),
    FieldsByName(
        what="a model written out and read back",
        source="""
            def moved(anchor: Anchor, line: int) -> Anchor:
                return Anchor.model_validate(dict(anchor.model_dump(), line=line))
        """,
        said="checked.py:3: `model_dump` writes a model out as a mapping",
    ),
    FieldsByName(
        what="a model written out into a variable first",
        source="""
            def moved(anchor: Anchor, line: int) -> Anchor:
                written = anchor.model_dump()
                written["line"] = line
                return Anchor(**written)
        """,
        said="checked.py:3: `model_dump` writes a model out as a mapping",
    ),
    FieldsByName(
        what="an object's fields read as a mapping",
        source="""
            def moved(anchor: Anchor, line: int) -> Anchor:
                return Anchor(**{**anchor.__dict__, "line": line})
        """,
        said="checked.py:3: `__dict__` reads an object's fields as a mapping",
    ),
    FieldsByName(
        what="an object's fields read by the builtin",
        source="""
            def moved(anchor: Anchor, line: int) -> Anchor:
                return Anchor(**{**vars(anchor), "line": line})
        """,
        said="checked.py:3: `vars` reads an object's fields as a mapping",
    ),
    FieldsByName(
        what="an object copied by its module's function",
        source="""
            import copy


            def moved(anchor: Anchor, line: int) -> Anchor:
                return copy.replace(anchor, line=line)
        """,
        said="checked.py:6: `copy.replace` copies an object by the names of its fields",
    ),
    FieldsByName(
        what="that module brought in under another name",
        source="""
            import copy as duplicating


            def moved(anchor: Anchor, line: int) -> Anchor:
                return duplicating.replace(anchor, line=line)
        """,
        said="checked.py:6: `copy.replace` copies an object by the names of its fields",
    ),
    FieldsByName(
        what="that module brought in inside a function",
        source="""
            def moved(anchor: Anchor, line: int) -> Anchor:
                import copy

                return copy.replace(anchor, line=line)
        """,
        said="checked.py:5: `copy.replace` copies an object by the names of its fields",
    ),
    FieldsByName(
        what="that function brought in by name",
        source="""
            from copy import replace
        """,
        said="checked.py:2: `copy.replace` copies an object by the names of its fields",
    ),
]

# A copy that names no field of the model, and is made past its constructor all the same
COPIED_WHOLE = """
    def kept(anchor: Anchor) -> Anchor:
        return anchor.model_copy(deep=True)
"""

# What takes no model apart: a model made by its constructor, one written as JSON, and mappings that never
# were models spread and merged
MODELS_MADE_AND_MAPPINGS_MERGED = """
    import os


    class Anchor(BaseModel):
        line: int

        def moved_to(self, line: int) -> Anchor:
            return Anchor(line=line)


    def answered(refusal: Refusal) -> Response:
        return Response(content=refusal.model_dump_json())


    def described(replies: dict[int, str], refusals: dict[int, str]) -> dict[int, str]:
        return {**replies, **refusals}


    def coloured(settings: dict[str, str]) -> dict[str, str]:
        return dict(os.environ) | settings


    def rendered(options: dict[str, str]) -> str:
        return render(**options)
"""

# A `replace` that is not the module `copy`'s: a text's, whatever the text is called, the system's, and one
# brought in from a module of the package's own that is called `copy`
REPLACES_OF_ANOTHER_KIND = """
    import os

    from .copy import replace


    def renamed(path: str) -> str:
        return path.replace("old", "new")


    def reworded(copy: str) -> str:
        return copy.replace("old", "new")


    def kept(staged: str, kept_as: str) -> None:
        os.replace(staged, kept_as)


    def reworded_by_the_package(text: str) -> str:
        return replace(text)
"""


def _check(tmp_path: Path, source: str) -> subprocess.CompletedProcess[str]:
    return _check_as(tmp_path, "checked.py", source)


def _check_as(tmp_path: Path, path: str, source: str) -> subprocess.CompletedProcess[str]:
    """Run the check on a directory that holds the source as the file of this path."""
    checked = tmp_path / path
    checked.parent.mkdir(parents=True, exist_ok=True)
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


@pytest.mark.parametrize("named", FIELDS_BY_NAME, ids=[named.what for named in FIELDS_BY_NAME])
def test_a_model_taken_apart_by_the_names_of_its_fields_is_named_where_it_is(
    tmp_path: Path, named: FieldsByName
) -> None:
    """Whatever is done with the mapping afterwards: the names it carries are text no type checker reads."""
    checked = _check(tmp_path, named.source)

    assert checked.returncode == RULE_BROKEN
    assert named.said in checked.stdout


def test_a_copy_that_changes_no_field_is_refused_all_the_same(tmp_path: Path) -> None:
    """A name cannot show which use it is, so the rule for `model_copy` holds here too, and says of it what is true."""
    checked = _check(tmp_path, COPIED_WHOLE)

    assert checked.returncode == RULE_BROKEN
    assert "checked.py:3: `model_copy` copies a model past its constructor, unchecked" in checked.stdout


def test_a_model_made_by_its_constructor_and_mappings_that_were_never_models_pass(tmp_path: Path) -> None:
    checked = _check(tmp_path, MODELS_MADE_AND_MAPPINGS_MERGED)

    assert (checked.returncode, checked.stdout) == (ALL_KEPT, "")


def test_a_script_that_starts_a_process_itself_is_named_where_it_does(tmp_path: Path) -> None:
    """Whatever name asyncio's way of starting one is reached by: imported, or asked of the module."""
    checked = _check_as(tmp_path, "scripts/looked.py", STARTS_PROCESSES)

    assert checked.returncode == RULE_BROKEN
    assert f"scripts/looked.py:3: `create_subprocess_shell` {A_SCRIPT_STARTS_NONE}" in checked.stdout
    assert f"scripts/looked.py:7: `create_subprocess_exec` {A_SCRIPT_STARTS_NONE}" in checked.stdout


@pytest.mark.parametrize("path", MAY_START_PROCESSES)
def test_the_script_that_runs_commands_and_a_file_that_is_no_script_may_start_a_process(
    tmp_path: Path, path: str
) -> None:
    checked = _check_as(tmp_path, path, STARTS_PROCESSES)

    assert (checked.returncode, checked.stdout) == (ALL_KEPT, "")


def test_a_replace_that_is_not_the_module_copys_passes(tmp_path: Path) -> None:
    """The rule is against one function of one module: a text's `replace`, the system's, a sibling module's are not it."""
    checked = _check(tmp_path, REPLACES_OF_ANOTHER_KIND)

    assert (checked.returncode, checked.stdout) == (ALL_KEPT, "")
