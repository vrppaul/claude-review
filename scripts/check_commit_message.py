"""Hold a commit's message to `.claude/rules/prose.md`: a short subject, a few lines of why, and no history.

The subject says what the commit makes true, the body why, and neither what the code was.
`conventional-pre-commit` holds the subject's form; this holds its length, the body's, and the words. Git's
own lines are no part of the message: its comments, the diff `git commit -v` shows under its scissors, and the
trailers of the last paragraph (`Co-Authored-By: …`).

Run by the commit-msg hook, in the project's own environment, on the file that holds the message:

    uv run python scripts/check_commit_message.py .git/COMMIT_EDITMSG

Prints each fault as `path:line: what is wrong` and exits 1, or says nothing and exits 0.
"""

import itertools
import re
import sys
from collections.abc import Iterator
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from faults import Fault, report
from history_words import TOLD_AS_HISTORY

ENCODING = "utf-8"
# Lines are counted from one, as an editor counts them
FIRST_LINE = 1
# The length git's own convention gives a subject, and the few lines of why the rule asks for
SUBJECT_CHARACTERS_AT_MOST = 72
BODY_LINES_AT_MOST = 5
GIT_COMMENT = "#"
# Under this line `git commit -v` shows the diff
SCISSORS = "# ------------------------ >8 ------------------------"
# A line git reads as a trailer when the message's last paragraph is all such lines
TRAILER = re.compile(r"^[A-Za-z][A-Za-z-]*: \S")
LONG_SUBJECT = "the subject is {found} characters where {most} are the most: say what the commit makes true"
LONG_BODY = "the body is {found} lines where {most} are the most: say why, with no list of files and no tally"
HISTORY = "`{found}` tells what the code was: say what the commit makes true"


class Line(BaseModel):
    """A line of the message, and its number in the file."""

    model_config = ConfigDict(frozen=True)

    number: int
    text: str


def faults_in(path: Path) -> list[Fault]:
    """What is wrong with the message a file holds: its subject's length, its body's, its history words."""
    written = _written(path.read_text(encoding=ENCODING))
    if not written:
        return []
    subject, *under_the_subject = written
    faults = [*_faults_of_size(path, subject, _body(under_the_subject)), *_faults_of_history(path, written)]
    return sorted(faults, key=lambda fault: fault.line)


def _faults_of_size(path: Path, subject: Line, body: list[Line]) -> Iterator[Fault]:
    """What is said of a subject too long, on its line, and of a body too long, on its first."""
    if len(subject.text) > SUBJECT_CHARACTERS_AT_MOST:
        says = LONG_SUBJECT.format(found=len(subject.text), most=SUBJECT_CHARACTERS_AT_MOST)
        yield Fault(path=path, line=subject.number, says=says)
    if len(body) > BODY_LINES_AT_MOST:
        first_of_body, *_ = body
        says = LONG_BODY.format(found=len(body), most=BODY_LINES_AT_MOST)
        yield Fault(path=path, line=first_of_body.number, says=says)


def _faults_of_history(path: Path, written: list[Line]) -> Iterator[Fault]:
    """What is said of each history word in the message, on its line."""
    for line in written:
        for found in TOLD_AS_HISTORY.finditer(line.text):
            yield Fault(path=path, line=line.number, says=HISTORY.format(found=found.group()))


def _written(message: str) -> list[Line]:
    """The lines the author wrote, numbered as in the file: none of git's comments, nothing under the scissors."""
    above_the_diff, _scissors, _diff = message.partition(SCISSORS)
    return [
        Line(number=number, text=text)
        for number, text in enumerate(above_the_diff.splitlines(), start=FIRST_LINE)
        if not text.startswith(GIT_COMMENT)
    ]


def _body(under_the_subject: list[Line]) -> list[Line]:
    """The lines that say why: none blank, and none of a last paragraph that is all trailers."""
    grouped = itertools.groupby(under_the_subject, key=lambda line: bool(line.text.strip()))
    paragraphs = [list(lines) for holds_words, lines in grouped if holds_words]
    match paragraphs:
        case [*earlier, last] if all(TRAILER.match(line.text) for line in last):
            paragraphs = earlier
    return [line for paragraph in paragraphs for line in paragraph]


def main(named: list[str]) -> int:
    [message_file] = named
    return report(faults_in(Path(message_file)))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
