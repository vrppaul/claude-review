"""Check the code rules no linter here can be told to keep.

No function is defined inside another: a helper is a function of its
module, with a name and parameters of its own, not a closure in the body of
something else. A lambda is still allowed where a short one does.

No name is too short to say what it holds: `index`, not `i`; `error`, not
`e`. A few words are short and still say what they mean, and `_` says that
nothing is kept.

No model's fields are named in text: a model is not copied with fields
updated (`model_copy(update=…)`), and one written out as a mapping
(`model_dump()`, `dict(model)`) is not spread with `**` or merged with `|`
into the making of another. No type checker reads the names such a mapping
carries. A model made from another is made by a method of the model, which
calls its constructor with every field written out. A mapping carried in a
variable before it is spread is past what this check can see: the rule
holds there all the same.

Run on files or directories, in the project's own environment, as the
pre-commit hook runs it and CI runs the hook:

    uv run python scripts/check_code_rules.py src scripts

Prints each place that breaks a rule and exits 1, or says nothing and exits 0.
"""

import ast
import sys
from pathlib import Path

from pydantic import BaseModel, ConfigDict

# Shorter than this, a name abbreviates what it holds rather than saying it
SHORTEST_NAME = 3
# Shorter than that, and still whole words; matched whatever their case
SHORT_WORDS = frozenset({"_", "id", "at", "to", "ok", "of", "on", "by", "is"})
PYTHON_FILES = "*.py"
FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)
# How pydantic copies a model with some of its fields changed
COPYING = "model_copy"
FIELDS_CHANGED = "update"
# How a model is written out as a mapping of its fields: by its own method, or by the builtin handed it
DUMPING = "model_dump"
MAPPING = "dict"
# What each way of naming a model's fields in text is told
COPIED_BY_NAME = "`model_copy(update=…)` names a model's fields in text: the model makes the copy, by its constructor"
SPREAD = "a model written out as a mapping is spread with `**`: its fields are named in text no type checker reads"
MERGED = "a model written out as a mapping is merged with `|`: its fields are named in text no type checker reads"
# What the process exits with
ALL_KEPT = 0
RULE_BROKEN = 1


class GivenName(BaseModel):
    """A name given to something, and the line it is given on."""

    model_config = ConfigDict(frozen=True)

    name: str
    line: int


class Breach(BaseModel):
    """One place that breaks a rule, and what it does."""

    model_config = ConfigDict(frozen=True)

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
            defined_inside = f"`{child.name}` is defined inside another function"
            found.append(Breach(path=path, line=child.lineno, says=defined_inside))
        given = _name_given(child)
        if given is not None and _too_short(given.name):
            too_short = f"`{given.name}` is too short to say what it holds"
            found.append(Breach(path=path, line=given.line, says=too_short))
        named_in_text = _fields_named_in_text(child, path)
        if named_in_text is not None:
            found.append(named_in_text)
        _look_inside(child, path, inside_function=inside_function or isinstance(child, FUNCTIONS), found=found)


def _fields_named_in_text(node: ast.AST, path: Path) -> Breach | None:
    """The breach a node makes by naming a model's fields in text, if it makes one.

    A copy with fields updated; a model written out as a mapping and spread
    into a call or into another mapping; one merged with another mapping.
    """
    match node:
        case ast.Call() if _copies_with_an_update(node):
            return Breach(path=path, line=node.lineno, says=COPIED_BY_NAME)
        case ast.Call() if _spreads_a_model_into_a_call(node):
            return Breach(path=path, line=node.lineno, says=SPREAD)
        case ast.Dict() if _spreads_a_model_into_a_mapping(node):
            return Breach(path=path, line=node.lineno, says=SPREAD)
        case ast.BinOp(op=ast.BitOr()) if _writes_a_model_out(node.left) or _writes_a_model_out(node.right):
            return Breach(path=path, line=node.lineno, says=MERGED)
        case _:
            return None


def _copies_with_an_update(call: ast.Call) -> bool:
    """Whether a call is `model.model_copy(update=…)`."""
    match call.func:
        case ast.Attribute(attr=called):
            return called == COPYING and any(keyword.arg == FIELDS_CHANGED for keyword in call.keywords)
        case _:
            return False


def _spreads_a_model_into_a_call(call: ast.Call) -> bool:
    """Whether a call is handed a model written out and spread: a spread is a keyword with no name."""
    return any(keyword.arg is None and _writes_a_model_out(keyword.value) for keyword in call.keywords)


def _spreads_a_model_into_a_mapping(written: ast.Dict) -> bool:
    """Whether a mapping written out has a model spread into it: a spread stands where a key would, with none."""
    return any(
        key is None and _writes_a_model_out(value) for key, value in zip(written.keys, written.values, strict=True)
    )


def _writes_a_model_out(node: ast.expr) -> bool:
    """Whether an expression writes a model out as a mapping of its fields: `model.model_dump(…)`, or `dict(model)`."""
    match node:
        case ast.Call(func=ast.Attribute(attr=called)):
            return called == DUMPING
        case ast.Call(func=ast.Name(id=called), args=[_], keywords=[]):
            return called == MAPPING
        case _:
            return False


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
            return GivenName(name=name, line=node.lineno)
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
