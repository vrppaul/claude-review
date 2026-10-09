"""Check the two code rules no linter here can be told to keep.

No function is defined inside another: a helper is a function of its
module, with a name and parameters of its own, not a closure in the body of
something else. A lambda is still allowed where a short one does.

No name is too short to say what it holds: `index`, not `i`; `error`, not
`e`. A few words are short and still say what they mean, and `_` says that
nothing is kept.

Run on files or directories, as CI and the pre-commit hook do:

    python3 scripts/check_code_rules.py src tests scripts

Prints each place that breaks a rule and exits 1, or says nothing and exits 0.
"""

import ast
import sys
from pathlib import Path
from typing import NamedTuple

# Shorter than this, a name abbreviates what it holds rather than saying it
SHORTEST_NAME = 3
# Shorter than that, and still whole words; matched whatever their case
SHORT_WORDS = frozenset({"_", "id", "at", "to", "ok", "of", "on", "by", "is"})
PYTHON_FILES = "*.py"
FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)
# What the process exits with
ALL_KEPT = 0
RULE_BROKEN = 1


class GivenName(NamedTuple):
    """A name given to something, and the line it is given on."""

    name: str
    line: int


class Breach(NamedTuple):
    """One place that breaks a rule, and what it does."""

    path: Path
    line: int
    says: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.says}"


def breaches_in(path: Path) -> list[Breach]:
    """Every place in one file that breaks a rule, in the order they are found."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[Breach] = []
    _look_inside(tree, path, inside_function=False, found=found)
    return found


def _look_inside(node: ast.AST, path: Path, *, inside_function: bool, found: list[Breach]) -> None:
    """Check everything under a node, knowing whether it already sits in a function."""
    for child in ast.iter_child_nodes(node):
        if inside_function and isinstance(child, FUNCTIONS):
            found.append(Breach(path, child.lineno, f"`{child.name}` is defined inside another function"))
        given = _name_given(child)
        if given is not None and _too_short(given.name):
            found.append(Breach(path, given.line, f"`{given.name}` is too short to say what it holds"))
        _look_inside(child, path, inside_function=inside_function or isinstance(child, FUNCTIONS), found=found)


def _name_given(node: ast.AST) -> GivenName | None:
    """The name a node gives to something — a variable, a parameter, a function, a class, an import — if any."""
    match node:
        case (
            ast.Name(id=name, ctx=ast.Store())
            | ast.Attribute(attr=name, ctx=ast.Store())
            | ast.arg(arg=name)
            | ast.FunctionDef(name=name)
            | ast.AsyncFunctionDef(name=name)
            | ast.ClassDef(name=name)
            | ast.ExceptHandler(name=str() as name)
            | ast.alias(asname=str() as name)
            | ast.MatchAs(name=str() as name)
            | ast.MatchStar(name=str() as name)
        ):
            return GivenName(name, node.lineno)
        case _:
            return None


def _too_short(name: str) -> bool:
    return len(name) < SHORTEST_NAME and name.lower() not in SHORT_WORDS


def _python_files(places: list[str]) -> list[Path]:
    """The Python files named, and those under the directories named."""
    files: list[Path] = []
    for place in map(Path, places):
        files.extend(sorted(place.rglob(PYTHON_FILES)) if place.is_dir() else [place])
    return files


def main(places: list[str]) -> int:
    breaches = [breach for path in _python_files(places) for breach in breaches_in(path)]
    for breach in breaches:
        print(breach)
    return RULE_BROKEN if breaches else ALL_KEPT


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
