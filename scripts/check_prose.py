"""Hold the comments and docstrings of Python files to `.claude/rules/prose.md`: no history, and no date.

A comment or a docstring says what stands; what changed, and when, a commit says. A phrase broken over two
lines is found all the same: comments on lines of their own, one right under another, are read as one passage,
as the lines of a docstring are.

Run in the repository's root, in the project's own environment, on the files named. The pre-commit hook hands
it every Python file outside `tests/`, and CI runs the hook:

    uv run python scripts/check_prose.py src/claude_review/services/unified_diff.py

Prints each fault as `path:line: what is wrong` and exits 1, or says nothing and exits 0.
"""

import ast
import bisect
import io
import itertools
import re
import sys
import tokenize
from collections.abc import Iterator
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from faults import Fault, report
from history_words import TOLD_AS_HISTORY

ENCODING = "utf-8"
COMMENT_SIGN = "#"
# What can open with a docstring
DOCUMENTED = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
# What a passage's lines are joined with, so a phrase broken over two of them is found
JOINT = " "
# A day written out, as git writes one
A_DATE = re.compile(r"\b20\d\d-\d\d-\d\d\b")
# Each pattern a passage may not hold, and what is said of what it finds
REFUSED = {
    TOLD_AS_HISTORY: "`{found}` tells what the code was: say what stands; what changed, a commit says",
    A_DATE: "`{found}` dates the prose: when it was written, a commit says",
}


class Line(BaseModel):
    """A line of prose, its comment sign and its indent left off, and its number in the file."""

    model_config = ConfigDict(frozen=True)

    number: int
    text: str


class Comment(BaseModel):
    """A comment, and whether it stands on a line of its own rather than after code."""

    model_config = ConfigDict(frozen=True)

    line: Line
    stands_alone: bool


def faults_in(path: Path) -> list[Fault]:
    """Every history word and every date in one file's comments and docstrings, by the line it is on."""
    text = path.read_text(encoding=ENCODING)
    passages = [*_comment_passages(text), *_docstrings(ast.parse(text, filename=str(path)))]
    return sorted((fault for passage in passages for fault in _faults_of(path, passage)), key=lambda fault: fault.line)


def _faults_of(path: Path, passage: list[Line]) -> Iterator[Fault]:
    """What is said of each refused word in one passage, on the line the word starts on."""
    text = JOINT.join(line.text for line in passage)
    # Where each line ends in the passage's text, the joint after it counted
    ends = list(itertools.accumulate(len(line.text) + len(JOINT) for line in passage))
    for pattern, says in REFUSED.items():
        for found in pattern.finditer(text):
            line = passage[bisect.bisect_right(ends, found.start())]
            yield Fault(path=path, line=line.number, says=says.format(found=found.group()))


def _comment_passages(text: str) -> Iterator[list[Line]]:
    """The comments of a file as passages: those on lines of their own, one right under another, are one."""
    passage: list[Comment] = []
    for comment in _comments(text):
        if passage and not _goes_on(passage[-1], comment):
            yield [held.line for held in passage]
            passage = []
        passage.append(comment)
    if passage:
        yield [held.line for held in passage]


def _goes_on(above: Comment, comment: Comment) -> bool:
    """Whether a comment goes on with the one above it: each on a line of its own, one right under the other."""
    return above.stands_alone and comment.stands_alone and above.line.number + 1 == comment.line.number


def _comments(text: str) -> Iterator[Comment]:
    """Every comment of a file, in order."""
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type == tokenize.COMMENT:
            line_number, _column = token.start
            words = Line(number=line_number, text=token.string.lstrip(COMMENT_SIGN).strip())
            yield Comment(line=words, stands_alone=token.line.lstrip().startswith(COMMENT_SIGN))


def _docstrings(tree: ast.Module) -> Iterator[list[Line]]:
    """The lines of every docstring that hold words, numbered as in the file."""
    for node in ast.walk(tree):
        if isinstance(node, DOCUMENTED) and (docstring := ast.get_docstring(node, clean=False)) is not None:
            first_statement, *_ = node.body
            numbered = enumerate(docstring.splitlines(), start=first_statement.lineno)
            yield [Line(number=number, text=text.strip()) for number, text in numbered if text.strip()]


def main(named: list[str]) -> int:
    return report([fault for name in named for fault in faults_in(Path(name))])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
