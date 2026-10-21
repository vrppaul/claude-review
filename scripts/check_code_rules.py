"""Check the code rules no linter here can be told to keep.

No function is defined inside another: a helper is a function of its
module, with a name and parameters of its own, not a closure in the body of
something else. A lambda is still allowed where a short one does.

No name is too short to say what it holds: `index`, not `i`; `error`, not
`e`. A few words are short and still say what they mean, and `_` says that
nothing is kept.

No model is taken apart into its fields by name, or put together from
them: a model made from another is made by a method of the model, which
calls its constructor with every field written out, where a type checker
reads the names. So what goes the other way is not used at all — pydantic's
`model_copy`, `model_construct` and `model_dump`, and Python's `__dict__`,
`vars` and `copy.replace`. A model leaves in a request or an answer as JSON
(`model_dump_json`), never as a mapping. The check knows these by name
alone: a model handed to `dict(…)`, or walked field by field, is past what
it sees, and the rule holds there all the same. A name is refused whatever
is done with it — `model_copy` also where it changes no field — since a
name does not show which use it is.

The module `copy` is known by the names the file's own imports give it,
wherever in the file they stand, so a file that does not import it may
call anything `copy`. In a file that does, whatever else goes by one of
those names is taken for the module: the check reads names, not what a
name stands for where it is used.

No script starts a command by asyncio's ways of starting one. A script runs
a command through `scripts/commands.py`, which gives the wait a limit and
stops what it started when the script is stopped. So four names are
refused: `create_subprocess_exec` and `create_subprocess_shell`, and the
event loop's `subprocess_exec` and `subprocess_shell`, wherever a file
writes one — imported, asked of a module or of a loop, or used bare. They
are refused in every Python file under a directory `scripts`, however deep
under it, but `commands.py` in that directory itself. That is all this
rule holds. bandit refuses the `subprocess` module and `os.system` in the
scripts already; a name put together in text, and Python's other ways of
starting a process (`os.fork`, `os.posix_spawn`, `pty.spawn`,
`multiprocessing`), are past what either sees. Nor is what a library
starts a script's to start here: Playwright starts the browser of a look.

A command of the command line takes every value by name, after `*`: click
hands its values over by name, and nothing calls a command with a bare
value in its place. A function is taken for a command by a decorator that
calls `command` or `group`, of click or of a group.

Every kind of refusal is kept in `claude_review/domain/exceptions.py`,
where the table that answers each kind with its status reads them. A class
built on anything the file imports from that module, by its name or asked
of the module, is a kind kept elsewhere.

Run on files or directories, in the project's own environment. The
pre-commit hook hands it every Python file outside `tests/`, and CI runs
the hook:

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
# What is said of a function defined inside another, and of a name too short
DEFINED_INSIDE = "`{name}` is defined inside another function"
TOO_SHORT = "`{name}` is too short to say what it holds"
# What takes a model apart into its fields by name, or puts one together from them, as an attribute of
# anything: each with what is said of it
FIELDS_BY_NAME = {
    "model_copy": "`model_copy` copies a model past its constructor, unchecked: the model makes its own copy",
    "model_construct": "`model_construct` builds a model unchecked, from names in text: build it by its constructor",
    "model_dump": "`model_dump` writes a model out as a mapping: hand the model on, or write it as JSON",
    "__dict__": "`__dict__` reads an object's fields as a mapping, by name: read the fields it has",
}
# The builtin that does as `__dict__` does, and the module and function that copy an object by the names of its fields
FIELDS_OF = "vars"
VARS_READ = "`vars` reads an object's fields as a mapping, by name: read the fields it has"
COPY_MODULE = "copy"
REPLACING = "replace"
REPLACED_BY_NAME = "`copy.replace` copies an object by the names of its fields: build it by its constructor"
# What starts a process, by the names asyncio and its event loop give it, however a file reaches them
PROCESS_STARTERS = frozenset(
    {"create_subprocess_exec", "create_subprocess_shell", "subprocess_exec", "subprocess_shell"}
)
# The directory the scripts are under, the one file right in it that may start a process, and what any other is told
SCRIPTS = "scripts"
RUNS_COMMANDS = "commands.py"
STARTED_BY_A_SCRIPT = (
    "`{name}` starts a process: a script starts one through `scripts/commands.py`, which stops what it starts"
)
# The decorators that make a function a command of the command line, called on click or on a group, and what is
# said of one that takes a value by position
COMMAND_DECORATORS = frozenset({"command", "group"})
BY_POSITION = "`{name}` is a command that takes a value by position: click hands every value over by name, after `*`"
# The module every kind of refusal is kept in, by its full name and its last, and what is said of a kind kept elsewhere
REFUSALS_MODULE = "claude_review.domain.exceptions"
REFUSALS_MODULE_NAME = "exceptions"
REFUSALS_PACKAGE = "claude_review.domain"
REFUSAL_ELSEWHERE = (
    "`{name}` is a kind of refusal kept outside `claude_review/domain/exceptions.py`, which keeps them all"
)
# What the process exits with
ALL_KEPT = 0
RULE_BROKEN = 1


class GivenName(BaseModel):
    """A name given to something, and the line it is given on."""

    model_config = ConfigDict(frozen=True)

    name: str
    line: int


class CheckedFile(BaseModel):
    """A file under the check: where it is, and what is known of it before any one node is looked at."""

    model_config = ConfigDict(frozen=True)

    path: Path
    # Every name the file's imports give the module `copy`: its own, or the one after `as`
    copy_module_names: frozenset[str]
    # Whether it may start a process itself: any file but a script, and of the scripts the one that runs commands
    may_start_processes: bool
    # Every name the file's imports bring in from the module of refusals, and every name they give that module
    refusal_names: frozenset[str]
    refusals_module_names: frozenset[str]


class Said(BaseModel):
    """What a rule says of a node that breaks it, and the line the node is on."""

    model_config = ConfigDict(frozen=True)

    line: int
    says: str


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
    file = CheckedFile(
        path=path,
        copy_module_names=_names_of_the_copy_module(tree),
        may_start_processes=_may_start_processes(path),
        refusal_names=_names_imported(tree, REFUSALS_MODULE),
        refusals_module_names=_names_given_to_the_refusals_module(tree),
    )
    _look_inside(tree, file, inside_function=False, found=found)
    return found


def _names_imported(tree: ast.AST, module: str) -> frozenset[str]:
    """Every name a file's imports bring in from a module, as the file calls it."""
    return frozenset(
        imported.asname or imported.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == module
        for imported in node.names
    )


def _names_given_to_the_refusals_module(tree: ast.AST) -> frozenset[str]:
    """Every name a file's imports give the module of refusals: imported from its package, or by its full name."""
    from_its_package = frozenset(
        imported.asname or imported.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == REFUSALS_PACKAGE
        for imported in node.names
        if imported.name == REFUSALS_MODULE_NAME
    )
    by_its_full_name = frozenset(
        imported.asname or imported.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for imported in node.names
        if imported.name == REFUSALS_MODULE
    )
    return from_its_package | by_its_full_name


def _may_start_processes(path: Path) -> bool:
    """Whether a file may start a process itself: one under no directory of scripts, or the one that runs commands."""
    is_a_script = SCRIPTS in path.parent.parts
    runs_commands = path.parent.name == SCRIPTS and path.name == RUNS_COMMANDS
    return runs_commands or not is_a_script


def _names_of_the_copy_module(tree: ast.AST) -> frozenset[str]:
    """Every name a file's imports give the module `copy`, wherever in the file it is imported."""
    return frozenset(
        imported.asname or imported.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for imported in node.names
        if imported.name == COPY_MODULE
    )


def _look_inside(node: ast.AST, file: CheckedFile, *, inside_function: bool, found: list[Breach]) -> None:
    """Check everything under a node, knowing whether it already sits in a function."""
    for child in ast.iter_child_nodes(node):
        said = [
            *_said_of_a_function_inside(child, inside_function=inside_function),
            *_said_of_a_short_name(child),
            *_said_of_fields_by_name(child, file.copy_module_names),
            *_said_of_a_process_started(child, may_start_processes=file.may_start_processes),
            *_said_of_a_command_by_position(child),
            *_said_of_a_refusal_elsewhere(child, file),
        ]
        found.extend(Breach(path=file.path, line=one.line, says=one.says) for one in said)
        _look_inside(child, file, inside_function=inside_function or isinstance(child, FUNCTIONS), found=found)


def _said_of_a_function_inside(node: ast.AST, *, inside_function: bool) -> list[Said]:
    """What is said of a function defined inside another: nothing of any other node."""
    match node:
        case ast.FunctionDef(name=name) | ast.AsyncFunctionDef(name=name) if inside_function:
            return [Said(line=node.lineno, says=DEFINED_INSIDE.format(name=name))]
        case _:
            return []


def _said_of_a_short_name(node: ast.AST) -> list[Said]:
    """What is said of a name given that is too short to say what it holds: nothing of any other node."""
    given = _name_given(node)
    if given is None or not _too_short(given.name):
        return []
    return [Said(line=given.line, says=TOO_SHORT.format(name=given.name))]


def _said_of_fields_by_name(node: ast.AST, copy_module_names: frozenset[str]) -> list[Said]:
    """What is said of a node that takes a model apart by the names of its fields, or puts one together from them.

    `copy_module_names` is what the node's file calls the module `copy`.
    """
    match node:
        case ast.Attribute(value=ast.Name(id=module), attr=name) if module in copy_module_names and name == REPLACING:
            return [Said(line=node.lineno, says=REPLACED_BY_NAME)]
        case ast.ImportFrom(module=module, names=names, level=0) if module == COPY_MODULE and _name_among(
            names, REPLACING
        ):
            return [Said(line=node.lineno, says=REPLACED_BY_NAME)]
        case ast.Attribute(attr=name) if name in FIELDS_BY_NAME:
            return [Said(line=node.lineno, says=FIELDS_BY_NAME[name])]
        case ast.Name(id=name) if name == FIELDS_OF:
            return [Said(line=node.lineno, says=VARS_READ)]
        case _:
            return []


def _said_of_a_process_started(node: ast.AST, *, may_start_processes: bool) -> list[Said]:
    """What is said of a node that names a way of starting a process, in a file that may not start one."""
    match node:
        case ast.Attribute(attr=name) | ast.Name(id=name) | ast.alias(name=name) if (
            not may_start_processes and name in PROCESS_STARTERS
        ):
            return [Said(line=node.lineno, says=STARTED_BY_A_SCRIPT.format(name=name))]
        case _:
            return []


def _said_of_a_command_by_position(node: ast.AST) -> list[Said]:
    """What is said of a command of the command line that takes a value by position: nothing of any other node."""
    match node:
        case ast.FunctionDef(name=name, args=arguments) | ast.AsyncFunctionDef(name=name, args=arguments) if (
            _is_a_command(node) and [*arguments.posonlyargs, *arguments.args]
        ):
            return [Said(line=node.lineno, says=BY_POSITION.format(name=name))]
        case _:
            return []


def _is_a_command(function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Whether a decorator of a function calls `command` or `group`, of click or of a group."""
    return any(
        isinstance(decorator, ast.Call)
        and isinstance(decorator.func, ast.Attribute)
        and decorator.func.attr in COMMAND_DECORATORS
        for decorator in function.decorator_list
    )


def _said_of_a_refusal_elsewhere(node: ast.AST, file: CheckedFile) -> list[Said]:
    """What is said of a class built on a kind of refusal, in a file other than the module that keeps them."""
    match node:
        case ast.ClassDef(name=name, bases=bases) if any(_is_a_refusal(base, file) for base in bases):
            return [Said(line=node.lineno, says=REFUSAL_ELSEWHERE.format(name=name))]
        case _:
            return []


def _is_a_refusal(base: ast.expr, file: CheckedFile) -> bool:
    """Whether a class's base is something the file brings in from the module of refusals."""
    match base:
        case ast.Name(id=name):
            return name in file.refusal_names
        case ast.Attribute(value=ast.Name(id=module)):
            return module in file.refusals_module_names
        case _:
            return False


def _name_among(imported: list[ast.alias], name: str) -> bool:
    """Whether a name is among those an import brings in."""
    return any(alias.name == name for alias in imported)


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
