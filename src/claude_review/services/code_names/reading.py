"""What a name is at a place in a file, and every place a name stands in one, as the file's grammar reads them.

Code is read by its language's grammar (`languages.py`): a word a comment or
a string holds is never a place a name stands. What no grammar reads — a
file of no language here, a Svelte component's markup — is read as text,
each whole word in it taken for a name. The names outlining a file, those
standing at its top, are read off the same definitions, each with the lines
it is defined on. Parsing is the CPU's work: whoever asks runs this off the
event loop.
"""

import re
import time
from bisect import bisect_right
from collections import defaultdict
from itertools import accumulate

import structlog
from pydantic import BaseModel, ConfigDict
from tree_sitter import Node, Parser, QueryCursor, Range

from claude_review.domain.code_names import (
    FIRST_COLUMN,
    HOLDS_CODE,
    OUTLINES,
    DefinitionKind,
    FoundAs,
    LinesOnSide,
    NameChange,
    NameDefined,
    NamePlace,
    TouchedName,
)
from claude_review.domain.exceptions import NoWordHereError
from claude_review.domain.models import FIRST_LINE, LineSide, LineSpan
from claude_review.services.code_names.languages import (
    CODE_CAPTURE,
    DEFINITION_CAPTURE,
    NAME_CAPTURE,
    EmbeddedCode,
    Grammar,
    code_files_of,
)
from claude_review.services.file_lines import LINE_END, NOT_TEXT, TEXT_ENCODING, line_text, lines_of

log = structlog.get_logger()

# A word of text no grammar reads, and the same word standing whole, as git matches one
WORD = re.compile(r"\w+")
WHOLE_WORD = r"(?<!\w){word}(?!\w)"

# The longest one file's parse may take before the file is read as one of no grammar. This repository's 18,199
# lines of code parse in 0.06 s; a long run of comment lines slows Python's grammar by its square, and a parse
# holds the interpreter, so every other request, while it runs
LONGEST_PARSE_SECONDS = 1.0


class ParseGivenUpError(Exception):
    """A file's parse ran past `LONGEST_PARSE_SECONDS` and was given up: its grammar says nothing of it."""


class LinePosition(BaseModel):
    """Where a character stands: its line, and its column in characters."""

    model_config = ConfigDict(frozen=True)

    line: int
    column: int


class SourceLines(BaseModel):
    """A file's bytes, its lines as git numbers them, and the byte each line starts at."""

    model_config = ConfigDict(frozen=True)

    content: bytes
    lines: list[bytes]
    starts: list[int]

    @classmethod
    def of(cls, content: bytes) -> SourceLines:
        """The lines of a file's bytes, each with the byte it starts at."""
        lines = lines_of(content)
        starts = list(accumulate((len(line) + len(LINE_END) for line in lines), initial=0))
        return cls(content=content, lines=lines, starts=starts)

    def text(self, line: int) -> str:
        return line_text(self.lines[line - FIRST_LINE])

    def offset_of(self, position: LinePosition) -> int:
        """The byte a character starts at."""
        before = self.text(position.line)[: position.column]
        return self.starts[position.line - FIRST_LINE] + len(before.encode(TEXT_ENCODING))

    def position_of(self, offset: int) -> LinePosition:
        """Where the character starting at a byte stands."""
        index = bisect_right(self.starts, offset) - 1
        before = self.lines[index][: offset - self.starts[index]].decode(TEXT_ENCODING, errors=NOT_TEXT)
        return LinePosition(line=index + FIRST_LINE, column=len(before))


class ReadCode(BaseModel):
    """A file's code as its grammar read it: its bytes, the tree, and the stretches of the file that are code."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    content: bytes
    root: Node
    grammar: Grammar
    # The stretches of the file the grammar read; None where it read the whole file
    stretches: list[Range] | None

    def text_of(self, node: Node) -> str:
        """What a node of the tree reads, from the file's bytes: a tree parsed from a callback holds none itself."""
        return self.content[node.start_byte : node.end_byte].decode(TEXT_ENCODING, errors=NOT_TEXT)

    def holds(self, offset: int) -> bool:
        """Whether the byte is one of the file's code."""
        return self.stretches is None or any(
            stretch.start_byte <= offset < stretch.end_byte for stretch in self.stretches
        )

    def name_around(self, start: int, end: int) -> Node | None:
        """The name these bytes stand in, if the grammar reads them as part of one."""
        node = self.root.named_descendant_for_byte_range(start, end)
        return node if node is not None and node.type in self.grammar.names else None

    def name_spanning(self, start: int, end: int) -> Node | None:
        """The name these bytes are, whole, if the grammar reads them as one."""
        name = self.name_around(start, end)
        return name if name is not None and name.start_byte == start and name.end_byte == end else None


class Definition(BaseModel):
    """A name defined: what it is defined as, where the name stands, and the bytes the whole definition spans."""

    model_config = ConfigDict(frozen=True)

    name: str
    kind: DefinitionKind
    name_start: int
    start: int
    end: int
    # Where it starts with its decorators: the first of the lines it is defined on, though no place in them is
    # inside it
    wrapped_start: int
    # Whether it stands in no scope of its own but the file's, as its grammar's scopes tell
    at_top: bool


class OutlinedName(BaseModel):
    """A name standing at the top of a file: what it is, where it is first named, and the lines each of its
    definitions spans, in the order of the file."""

    model_config = ConfigDict(frozen=True)

    name: str
    kind: DefinitionKind
    named_at: LinePosition
    spans: list[LineSpan]

    def lines_on(self, side: LineSide) -> LinesOnSide:
        """The lines it is defined on, first to last, numbered on the side of the diff its file is read on."""
        return LinesOnSide(
            side=side, first=min(span.first for span in self.spans), last=max(span.last for span in self.spans)
        )

    def touched(self, change: NameChange, stands_on: list[LinesOnSide]) -> TouchedName:
        """The name as one the change touched, with what became of it and the lines it stands on, side by side."""
        return TouchedName(
            name=self.name,
            defined_as=self.kind,
            change=change,
            line=self.named_at.line,
            column=self.named_at.column,
            stands_on=stands_on,
        )

    def defined_in(self, path: str) -> NameDefined:
        """The name as one the file at this path of the take defines."""
        return NameDefined(
            name=self.name,
            defined_as=self.kind,
            path=path,
            line=self.named_at.line,
            column=self.named_at.column,
        )


def word_at(path: str, content: bytes, line: int, column: int) -> str:
    """The word at a place in a file: the name the grammar reads there, or else the word of text the place is in.

    A column may stand at the end of its line, where a click past the last
    character lands: the place then holds no word.

    Raises:
        NoWordHereError: if the file has no such line, the line no such column, or the place holds no word.
    """
    source = SourceLines.of(content)
    if not FIRST_LINE <= line <= len(source.lines):
        msg = f"{path} has no line {line}"
        raise NoWordHereError(msg)
    text = source.text(line)
    if not FIRST_COLUMN <= column <= len(text):
        msg = f"line {line} of {path} has no column {column}"
        raise NoWordHereError(msg)
    name = _name_at(path, source, LinePosition(line=line, column=column)) if column < len(text) else None
    word = name or _word_around(text, column)
    if word is None:
        msg = f"line {line}, column {column} of {path} holds no word"
        raise NoWordHereError(msg)
    return word


def places_of(path: str, content: bytes, name: str, added_lines: frozenset[int]) -> list[NamePlace]:
    """Every place a name stands in a file, in the order of the file; `added_lines` are those the change wrote."""
    source = SourceLines.of(content)
    code = _read_code(path, content)
    named = [] if code is None else _named_places(path, source, code, name, added_lines)
    texts = _text_places(path, source, code, name, added_lines)
    return sorted([*named, *texts], key=lambda place: (place.line, place.column))


def outline(path: str, content: bytes) -> list[OutlinedName] | None:
    """The names outlining a file, each once, in the order of the file; none in a file of no grammar, and None
    where its parse was given up, so nothing can be said of what it outlines."""
    try:
        code = _code_of(path, content)
    except ParseGivenUpError:
        return None
    if code is None:
        return []
    source = SourceLines.of(content)
    outlining: defaultdict[str, list[Definition]] = defaultdict(list)
    for definition in sorted(_definitions(code).values(), key=lambda definition: definition.name_start):
        if definition.kind in OUTLINES and definition.at_top:
            outlining[definition.name].append(definition)
    return [_outlined(source, defined) for defined in outlining.values()]


def _name_at(path: str, source: SourceLines, position: LinePosition) -> str | None:
    """The name the file's grammar reads at a character, if the character is code and a name's."""
    code = _read_code(path, source.content)
    start = source.offset_of(position)
    if code is None or not code.holds(start):
        return None
    character = source.text(position.line)[position.column]
    name = code.name_around(start, start + len(character.encode(TEXT_ENCODING)))
    return None if name is None else code.text_of(name)


def _read_code(path: str, content: bytes) -> ReadCode | None:
    """A file's code read by its grammar, for the lookup; None where it has none to read, or its parse was given up:
    the lookup then reads the file as text."""
    try:
        return _code_of(path, content)
    except ParseGivenUpError:
        return None


def _code_of(path: str, content: bytes) -> ReadCode | None:
    """A file's code read by its grammar; None for a file of no grammar here, or none of whose stretches is code.

    Raises:
        ParseGivenUpError: if parsing the file runs past `LONGEST_PARSE_SECONDS`.
    """
    files = code_files_of(path)
    if files is None:
        return None
    deadline = time.perf_counter() + LONGEST_PARSE_SECONDS
    stretches = None if files.embedded_in is None else _stretches(path, files.embedded_in, content, deadline)
    # A file of another language holding no code has none to read
    if stretches is not None and not stretches:
        return None
    parser = Parser(files.grammar.language, included_ranges=stretches)
    root = _parsed(parser, path, content, deadline)
    return ReadCode(content=content, root=root, grammar=files.grammar, stretches=stretches)


def _stretches(path: str, embedded: EmbeddedCode, content: bytes, deadline: float) -> list[Range]:
    """The stretches of a file that hold its code, in the order of the file.

    Raises:
        ParseGivenUpError: if parsing the file runs past the deadline.
    """
    root = _parsed(Parser(embedded.language), path, content, deadline)
    captured = QueryCursor(embedded.stretches).captures(root).get(CODE_CAPTURE, [])
    return [node.range for node in sorted(captured, key=lambda node: node.start_byte)]


def _parsed(parser: Parser, path: str, content: bytes, deadline: float) -> Node:
    """The root of the tree a parser reads a file as.

    Raises:
        ParseGivenUpError: if the parse runs past the deadline.
    """
    try:
        tree = parser.parse(
            lambda offset, _point: content[offset:],
            progress_callback=lambda _offset, _has_error: time.perf_counter() > deadline,
        )
    except ValueError as halted:
        # What tree-sitter raises for a parse its progress callback halted
        log.warning("parse_given_up", path=path, size=len(content))
        msg = f"parsing {path} ran past {LONGEST_PARSE_SECONDS} s"
        raise ParseGivenUpError(msg) from halted
    return tree.root_node


def _named_places(
    path: str, source: SourceLines, code: ReadCode, name: str, added_lines: frozenset[int]
) -> list[NamePlace]:
    """Every place the grammar reads the name at, each with what it defines and the code it stands inside."""
    definitions = _definitions(code)
    holding_code = [definition for definition in definitions.values() if definition.kind in HOLDS_CODE]
    wanted = name.encode(TEXT_ENCODING)
    places = []
    for start in _occurrences(source.content, wanted):
        if not code.holds(start) or code.name_spanning(start, start + len(wanted)) is None:
            continue
        position = source.position_of(start)
        defined = definitions.get(start)
        places.append(
            NamePlace(
                path=path,
                line=position.line,
                column=position.column,
                text=source.text(position.line),
                defined_as=None if defined is None else defined.kind,
                inside=_inside(holding_code, start),
                added=position.line in added_lines,
                found_as=FoundAs.NAME,
            )
        )
    return places


def _text_places(
    path: str, source: SourceLines, code: ReadCode | None, name: str, added_lines: frozenset[int]
) -> list[NamePlace]:
    """The lines of text no grammar reads that hold the name as a whole word, a place to each, at its first."""
    if code is not None and code.stretches is None:
        return []
    whole_word = re.compile(WHOLE_WORD.format(word=re.escape(name)))
    wanted = name.encode(TEXT_ENCODING)
    places = []
    for index, line_bytes in enumerate(source.lines):
        if wanted not in line_bytes:
            continue
        line = index + FIRST_LINE
        column = _first_outside_code(source, code, whole_word, line)
        if column is not None:
            places.append(
                NamePlace(
                    path=path,
                    line=line,
                    column=column,
                    text=source.text(line),
                    defined_as=None,
                    inside=None,
                    added=line in added_lines,
                    found_as=FoundAs.TEXT,
                )
            )
    return places


def _first_outside_code(
    source: SourceLines, code: ReadCode | None, whole_word: re.Pattern[str], line: int
) -> int | None:
    """The column of the first whole word on a line that stands outside the file's code, if any does."""
    for match in whole_word.finditer(source.text(line)):
        position = LinePosition(line=line, column=match.start())
        if code is None or not code.holds(source.offset_of(position)):
            return position.column
    return None


def _definitions(code: ReadCode) -> dict[int, Definition]:
    """Every definition in the code, by the byte its name starts at; of two of one name, the first pattern's."""
    definitions: dict[int, Definition] = {}
    matches = QueryCursor(code.grammar.definitions).matches(code.root)
    for _, captures in sorted(matches, key=lambda match: match[0]):
        definition = _definition_of(captures, code)
        definitions.setdefault(definition.name_start, definition)
    return definitions


def _definition_of(captures: dict[str, list[Node]], code: ReadCode) -> Definition:
    """The definition one match of a query captures: the name, and the node of the definition under its kind."""
    [name] = captures[NAME_CAPTURE]
    [kind] = [capture for capture in captures if capture.startswith(DEFINITION_CAPTURE)]
    [defined] = captures[kind]
    wrapped = _wrapped(defined, code.grammar.wrappers)
    return Definition(
        name=code.text_of(name),
        kind=DefinitionKind(kind.removeprefix(DEFINITION_CAPTURE)),
        name_start=name.start_byte,
        start=defined.start_byte,
        end=defined.end_byte,
        wrapped_start=wrapped.start_byte,
        at_top=_at_top(wrapped, code.grammar.scopes),
    )


def _wrapped(defined: Node, wrappers: frozenset[str]) -> Node:
    """The outermost of the nodes that wrap a definition with its decorators, or the definition where none does."""
    wrapping = defined
    while wrapping.parent is not None and wrapping.parent.type in wrappers:
        wrapping = wrapping.parent
    return wrapping


def _at_top(node: Node, scopes: frozenset[str]) -> bool:
    """Whether no node holding this one opens a scope of its own."""
    holding = node.parent
    while holding is not None and holding.type not in scopes:
        holding = holding.parent
    return holding is None


def _outlined(source: SourceLines, definitions: list[Definition]) -> OutlinedName:
    """A name outlining a file, from its definitions in the order of the file: the first says what it is."""
    [first, *_] = definitions
    return OutlinedName(
        name=first.name,
        kind=first.kind,
        named_at=source.position_of(first.name_start),
        spans=[_lines_of(source, definition) for definition in definitions],
    )


def _lines_of(source: SourceLines, definition: Definition) -> LineSpan:
    """The lines a definition spans, from the one its decorators start on to the one its last byte is on."""
    return LineSpan(
        first=source.position_of(definition.wrapped_start).line, last=source.position_of(definition.end - 1).line
    )


def _inside(definitions: list[Definition], offset: int) -> str | None:
    """The name of the innermost of these definitions a place stands inside, other than one it names."""
    around = [
        definition
        for definition in definitions
        if definition.start <= offset < definition.end and definition.name_start != offset
    ]
    return max(around, key=lambda definition: definition.start).name if around else None


def _occurrences(content: bytes, wanted: bytes) -> list[int]:
    """Every byte the wanted bytes start at in the content."""
    starts = []
    start = content.find(wanted)
    while start >= 0:
        starts.append(start)
        start = content.find(wanted, start + 1)
    return starts


def _word_around(text: str, column: int) -> str | None:
    """The word of text a column stands in, if any."""
    return next((word.group() for word in WORD.finditer(text) if word.start() <= column < word.end()), None)
