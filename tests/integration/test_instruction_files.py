"""The check that holds the instruction files to their size, the paths they name and their places.

Run as the hook runs it, in a repository of its own: `AGENTS.md`, the rules
of one area under `.claude/rules/`, and `CLAUDE.md` linked to the first.
"""

import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest
from pydantic import BaseModel, ConfigDict

CHECK = Path(__file__).parents[2] / "scripts" / "check_instruction_files.py"
# What the check exits with: a fault found, or every file kept
FAULT_FOUND = 1
ALL_KEPT = 0

# What a file may hold: the general file and the rules of an area in bytes, either in lines, a line in characters
GENERAL_BYTES = 6_500
AREA_BYTES = 5_000
MOST_LINES = 100
LONGEST_LINE = 240

# What a file that outgrew its bytes or its lines is told, and a line that outgrew its characters
WHERE_IT_GOES = (
    "move a rule for one area to that area's file, how a thing is built to its module's docstring, "
    "what a tool can hold to a gate"
)
A_SHORTER_LINE = f"1 over the {LONGEST_LINE} a line may hold: a rule is a short imperative, so cut it or make it two"
# What a path that is not there is told, a file of rules the general file leaves out, and one that names no paths
FROM_THE_ROOT = "write the path from the repository's root, to what is there"
A_LINE_AMONG_THE_AREAS = "give it a line there, among the rules by area, saying when to read it"
HOW_RULES_OPEN = 'open it with `---`, `paths:`, a line `  - "pattern"` for each pattern, `---`'
# What a file that cannot be read as UTF-8 is told, and the rules of an area saved as Latin-1: its é is one byte, 0xE9
SAVE_IT_AS_UTF8 = "is not written as UTF-8, so nothing in it can be read or counted: save it as UTF-8"
RULES_IN_LATIN_1 = "- Ask the server through a café.\n".encode("latin-1")
# What is said of a `CLAUDE.md` that is anything but the link
NOT_THE_LINK = (
    "CLAUDE.md: is not a symlink to AGENTS.md, which is how Claude Code is given the rules: ln -s AGENTS.md CLAUDE.md"
)

# Seven lines, the last of them naming the rules of an area: its dash takes three bytes, so bytes and characters differ
GENERAL_RULES = dedent("""\
    # A project

    - Tests first.

    ## Rules by area

    - `.claude/rules/page.md` — anything under `frontend/`.
    """)

PAGE_RULES = dedent("""\
    ---
    paths:
      - "frontend/**"
    ---

    - Ask the server through `frontend/request.ts`.
    """)

# A line of filler a hundred bytes long with its end, and a rule on a line of its own
FILLER_LINE = "x" * 99 + "\n"
A_RULE = "- A rule.\n"


class Written(BaseModel):
    """A file of a repository: where it is from the root, and what it says."""

    model_config = ConfigDict(frozen=True)

    path: str
    text: str


class Refused(BaseModel):
    """A repository the check refuses: what is wrong in it, its files, and the one thing said of it."""

    model_config = ConfigDict(frozen=True)

    what: str
    files: list[Written]
    said: str


class Passed(BaseModel):
    """A repository the check passes: what is true of it, and its files."""

    model_config = ConfigDict(frozen=True)

    what: str
    files: list[Written]


def _holding_bytes(text: str, size: int) -> str:
    """The text grown to hold exactly this many bytes, in lines none of them too long."""
    missing = size - len(text.encode())
    return text + FILLER_LINE * (missing // len(FILLER_LINE)) + "x" * (missing % len(FILLER_LINE))


def _holding_lines(text: str, lines: int) -> str:
    """The text grown to exactly this many lines."""
    return text + A_RULE * (lines - len(text.splitlines()))


def _holding_a_line_of(text: str, length: int) -> str:
    """The text with one more line under it, this many characters long."""
    return text + "x" * length + "\n"


GENERAL = Written(path="AGENTS.md", text=GENERAL_RULES)
PAGE = Written(path=".claude/rules/page.md", text=PAGE_RULES)
REQUEST = Written(path="frontend/request.ts", text="")
# A later file of the same path is written over an earlier one: a case names only the file it changes
KEPT = [GENERAL, PAGE, REQUEST]

OUTGROWN = [
    Refused(
        what="the general file a byte over",
        files=[*KEPT, Written(path="AGENTS.md", text=_holding_bytes(GENERAL_RULES, GENERAL_BYTES + 1))],
        said=f"AGENTS.md: holds {GENERAL_BYTES + 1} bytes, 1 over its {GENERAL_BYTES}: {WHERE_IT_GOES}",
    ),
    Refused(
        what="the general file a line over",
        files=[*KEPT, Written(path="AGENTS.md", text=_holding_lines(GENERAL_RULES, MOST_LINES + 1))],
        said=f"AGENTS.md: holds {MOST_LINES + 1} lines, 1 over its {MOST_LINES}: {WHERE_IT_GOES}",
    ),
    Refused(
        what="a line of the general file a character over",
        files=[*KEPT, Written(path="AGENTS.md", text=_holding_a_line_of(GENERAL_RULES, LONGEST_LINE + 1))],
        said=f"AGENTS.md:8: a line of {LONGEST_LINE + 1} characters, {A_SHORTER_LINE}",
    ),
    Refused(
        what="the rules of an area a byte over",
        files=[*KEPT, Written(path=".claude/rules/page.md", text=_holding_bytes(PAGE_RULES, AREA_BYTES + 1))],
        said=f".claude/rules/page.md: holds {AREA_BYTES + 1} bytes, 1 over its {AREA_BYTES}: {WHERE_IT_GOES}",
    ),
    Refused(
        what="the rules of an area a line over",
        files=[*KEPT, Written(path=".claude/rules/page.md", text=_holding_lines(PAGE_RULES, MOST_LINES + 1))],
        said=f".claude/rules/page.md: holds {MOST_LINES + 1} lines, 1 over its {MOST_LINES}: {WHERE_IT_GOES}",
    ),
    Refused(
        what="a line of the rules of an area a character over",
        files=[*KEPT, Written(path=".claude/rules/page.md", text=_holding_a_line_of(PAGE_RULES, LONGEST_LINE + 1))],
        said=f".claude/rules/page.md:7: a line of {LONGEST_LINE + 1} characters, {A_SHORTER_LINE}",
    ),
]

FULL = [
    Passed(
        what="the general file of every byte it may hold",
        files=[*KEPT, Written(path="AGENTS.md", text=_holding_bytes(GENERAL_RULES, GENERAL_BYTES))],
    ),
    Passed(
        what="the general file of every line it may hold",
        files=[*KEPT, Written(path="AGENTS.md", text=_holding_lines(GENERAL_RULES, MOST_LINES))],
    ),
    Passed(
        what="a line of the general file as long as a line may be",
        files=[*KEPT, Written(path="AGENTS.md", text=_holding_a_line_of(GENERAL_RULES, LONGEST_LINE))],
    ),
    Passed(
        what="the rules of an area of every byte they may hold",
        files=[*KEPT, Written(path=".claude/rules/page.md", text=_holding_bytes(PAGE_RULES, AREA_BYTES))],
    ),
    Passed(
        what="the rules of an area of every line they may hold",
        files=[*KEPT, Written(path=".claude/rules/page.md", text=_holding_lines(PAGE_RULES, MOST_LINES))],
    ),
    Passed(
        what="a line of the rules of an area as long as a line may be",
        files=[*KEPT, Written(path=".claude/rules/page.md", text=_holding_a_line_of(PAGE_RULES, LONGEST_LINE))],
    ),
]

NAMING_NOTHING = [
    Refused(
        what="a file that is not there",
        files=[*KEPT, Written(path="AGENTS.md", text=GENERAL_RULES + "- Read `src/review.py` first.\n")],
        said=f"AGENTS.md:8: `src/review.py` names nothing in the repository: {FROM_THE_ROOT}",
    ),
    Refused(
        what="a file named without its directories",
        files=[*KEPT, Written(path="AGENTS.md", text=GENERAL_RULES + "- Ask the server through `request.ts`.\n")],
        said=f"AGENTS.md:8: `request.ts` names nothing in the repository: {FROM_THE_ROOT}",
    ),
    Refused(
        what="a directory inside a command",
        files=[*KEPT, Written(path="AGENTS.md", text=GENERAL_RULES + "- Run `uv run pytest tests/unit/`.\n")],
        said=f"AGENTS.md:8: `tests/unit/` names nothing in the repository: {FROM_THE_ROOT}",
    ),
    Refused(
        what="a pattern that matches nothing",
        files=[*KEPT, Written(path="AGENTS.md", text=GENERAL_RULES + "- The server is `backend/**`.\n")],
        said=f"AGENTS.md:8: `backend/**` names nothing in the repository: {FROM_THE_ROOT}",
    ),
    Refused(
        what="a file of rules nobody wrote",
        files=[*KEPT, Written(path="AGENTS.md", text=GENERAL_RULES + "- `.claude/rules/server.md` — the server.\n")],
        said=f"AGENTS.md:8: `.claude/rules/server.md` names nothing in the repository: {FROM_THE_ROOT}",
    ),
]

# What is there, named every way a path is; and code that is no path of the repository, though it holds what
# a path holds: an address the server answers, a name with a dot in it, the marks a pattern is made of
THERE_OR_NO_PATH = GENERAL_RULES + dedent("""\
    - A directory, `frontend/`; a pattern, `frontend/**`; a file inside a command, `cat frontend/request.ts`.
    - A file at the root, `AGENTS.md`, and one that only links to it, `CLAUDE.md`.
    - The server's own addresses: `/`, `/assets`, `GET /api/images/{image_id}`.
    - Code with a dot or a mark in it: `$state.raw`, `review.story.numbering`, `str | None`, `*`, `[`.
    """)

RULES_OF_NO_PATHS = "- Ask the server through `frontend/request.ts`.\n"

RULES_OF_PATHS_NOT_THERE = dedent("""\
    ---
    paths:
      - "frontend/**"
      - "backend/**"
    ---

    - Ask the server through `frontend/request.ts`.
    """)


def _written(root: Path, files: list[Written]) -> Path:
    """A repository holding these files and nothing else."""
    for file in files:
        placed = root / file.path
        placed.parent.mkdir(parents=True, exist_ok=True)
        placed.write_text(file.text)
    return root


def _linked(repository: Path) -> Path:
    """The repository with `CLAUDE.md` a link to `AGENTS.md`, as Claude Code reads the one for the other."""
    (repository / "CLAUDE.md").symlink_to("AGENTS.md")
    return repository


def _check(repository: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(CHECK)], cwd=repository, capture_output=True, text=True, check=False)


def test_files_within_their_size_that_name_what_is_there_pass(tmp_path: Path) -> None:
    checked = _check(_linked(_written(tmp_path, KEPT)))

    assert (checked.returncode, checked.stdout) == (ALL_KEPT, "")


@pytest.mark.parametrize("outgrown", OUTGROWN, ids=[outgrown.what for outgrown in OUTGROWN])
def test_a_file_that_holds_more_than_it_may_is_told_where_the_rest_belongs(tmp_path: Path, outgrown: Refused) -> None:
    """Bytes, not characters: the general file's dash is three of them, and one byte over is over."""
    checked = _check(_linked(_written(tmp_path, outgrown.files)))

    assert (checked.returncode, checked.stdout.splitlines()) == (FAULT_FOUND, [outgrown.said])


@pytest.mark.parametrize("full", FULL, ids=[full.what for full in FULL])
def test_a_file_that_holds_exactly_what_it_may_passes(tmp_path: Path, full: Passed) -> None:
    checked = _check(_linked(_written(tmp_path, full.files)))

    assert (checked.returncode, checked.stdout) == (ALL_KEPT, "")


@pytest.mark.parametrize("naming", NAMING_NOTHING, ids=[naming.what for naming in NAMING_NOTHING])
def test_a_path_that_names_nothing_in_the_repository_is_named_where_it_is_written(
    tmp_path: Path, naming: Refused
) -> None:
    """A path is written from the root, whole: a file moved, or named by its last part, is found when it is committed."""
    checked = _check(_linked(_written(tmp_path, naming.files)))

    assert (checked.returncode, checked.stdout.splitlines()) == (FAULT_FOUND, [naming.said])


def test_what_is_there_and_code_that_is_no_path_pass(tmp_path: Path) -> None:
    checked = _check(_linked(_written(tmp_path, [*KEPT, Written(path="AGENTS.md", text=THERE_OR_NO_PATH)])))

    assert (checked.returncode, checked.stdout) == (ALL_KEPT, "")


def test_a_file_of_rules_the_general_file_does_not_name_is_refused(tmp_path: Path) -> None:
    """Whoever is not Claude Code reaches an area's rules by their line in the general file alone."""
    unnamed = Written(path=".claude/rules/tests.md", text=PAGE_RULES)

    checked = _check(_linked(_written(tmp_path, [*KEPT, unnamed])))

    assert (checked.returncode, checked.stdout.splitlines()) == (
        FAULT_FOUND,
        [f".claude/rules/tests.md: AGENTS.md does not name this file: {A_LINE_AMONG_THE_AREAS}"],
    )


def test_rules_that_do_not_open_with_the_paths_they_are_for_are_refused(tmp_path: Path) -> None:
    """Without them an area's rules are no longer an area's: every session reads them."""
    for_no_paths = Written(path=".claude/rules/page.md", text=RULES_OF_NO_PATHS)

    checked = _check(_linked(_written(tmp_path, [*KEPT, for_no_paths])))

    assert (checked.returncode, checked.stdout.splitlines()) == (
        FAULT_FOUND,
        [
            ".claude/rules/page.md: does not open with the paths it is rules for, "
            f"so every session would read it: {HOW_RULES_OPEN}"
        ],
    )


def test_rules_for_a_pattern_no_file_matches_are_refused_at_the_pattern(tmp_path: Path) -> None:
    for_paths_not_there = Written(path=".claude/rules/page.md", text=RULES_OF_PATHS_NOT_THERE)

    checked = _check(_linked(_written(tmp_path, [*KEPT, for_paths_not_there])))

    assert (checked.returncode, checked.stdout.splitlines()) == (
        FAULT_FOUND,
        [
            ".claude/rules/page.md:4: no file matches `backend/**`, so no file opened brings these rules: name what is there"
        ],
    )


def test_rules_for_a_pattern_that_matches_a_directory_and_no_file_are_refused(tmp_path: Path) -> None:
    """Claude Code loads rules when it opens a file: a directory with nothing in it brings them to nobody."""
    repository = _written(tmp_path, [*KEPT, Written(path=".claude/rules/page.md", text=RULES_OF_PATHS_NOT_THERE)])
    (repository / "backend").mkdir()

    checked = _check(_linked(repository))

    assert (checked.returncode, checked.stdout.splitlines()) == (
        FAULT_FOUND,
        [
            ".claude/rules/page.md:4: no file matches `backend/**`, so no file opened brings these rules: name what is there"
        ],
    )


def test_a_path_that_leaves_the_repository_names_nothing_in_it_though_a_file_is_there(tmp_path: Path) -> None:
    (tmp_path / "outside").mkdir()
    (tmp_path / "outside" / "notes.md").write_text("Notes kept beside the repository.\n")
    leaving = Written(path="AGENTS.md", text=GENERAL_RULES + "- Read `../outside/notes.md` first.\n")

    checked = _check(_linked(_written(tmp_path / "repository", [*KEPT, leaving])))

    assert (checked.returncode, checked.stdout.splitlines()) == (
        FAULT_FOUND,
        [f"AGENTS.md:8: `../outside/notes.md` names nothing in the repository: {FROM_THE_ROOT}"],
    )


def test_a_file_that_is_not_written_as_utf8_is_refused_by_name_and_nothing_more_is_said(tmp_path: Path) -> None:
    repository = _written(tmp_path, KEPT)
    (repository / ".claude" / "rules" / "page.md").write_bytes(RULES_IN_LATIN_1)

    checked = _check(_linked(repository))

    assert (checked.returncode, checked.stdout.splitlines(), checked.stderr) == (
        FAULT_FOUND,
        [f".claude/rules/page.md: {SAVE_IT_AS_UTF8}"],
        "",
    )


def test_claude_md_as_a_file_of_its_own_is_refused(tmp_path: Path) -> None:
    """Claude Code reads `CLAUDE.md` alone where there is one: a file there stands in place of the rules."""
    of_its_own = Written(path="CLAUDE.md", text="See AGENTS.md.\n")

    checked = _check(_written(tmp_path, [*KEPT, of_its_own]))

    assert (checked.returncode, checked.stdout.splitlines()) == (FAULT_FOUND, [NOT_THE_LINK])


def test_claude_md_linked_to_another_file_is_refused(tmp_path: Path) -> None:
    repository = _written(tmp_path, KEPT)
    (repository / "CLAUDE.md").symlink_to(".claude/rules/page.md")

    checked = _check(repository)

    assert (checked.returncode, checked.stdout.splitlines()) == (FAULT_FOUND, [NOT_THE_LINK])


def test_a_repository_without_its_general_file_is_refused(tmp_path: Path) -> None:
    checked = _check(_linked(_written(tmp_path, [PAGE, REQUEST])))

    assert (checked.returncode, checked.stdout.splitlines()) == (
        FAULT_FOUND,
        ["AGENTS.md: is not in the repository: it holds the rules every agent reads"],
    )
