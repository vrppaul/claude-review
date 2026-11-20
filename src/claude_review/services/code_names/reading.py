"""What a name is at a place in a file, and every place a name stands in one, as the file's grammar reads them.

Code is read by its language's grammar (`languages.py`): a word a comment or
a string holds is never a place a name stands. What no grammar reads — a
file of no language here, a Svelte component's markup — is read as text,
each whole word in it taken for a name. Parsing is the CPU's work: whoever
asks runs this off the event loop.
"""

import re
from bisect import bisect_right
from itertools import accumulate

from pydantic import BaseModel, ConfigDict
from tree_sitter import Node, Parser, QueryCursor, Range

from claude_review.domain.code_names import FIRST_COLUMN, HOLDS_CODE, DefinitionKind, FoundAs, NamePlace
from claude_review.domain.exceptions import NoWordHereError
from claude_review.domain.models import FIRST_LINE
from claude_review.services.code_names.languages import (
    CODE_CAPTURE,
    DEFINITION_CAPTURE,
    NAME_CAPTURE,
    CodeFiles,
    EmbeddedCode,
    Grammar,
    code_files_of,
)

# What ends a line, and nothing else does: git numbers a file's lines by it
LINE_END = b"\n"
# What a file's bytes are read as; a byte that is not is replaced, as the diff shows it
TEXT_ENCODING = "utf-8"
NOT_TEXT = "replace"
# A word of text no grammar reads, and the same word standing whole, as git matches one
WORD = re.compile(r"\w+")
WHOLE_WORD = r"(?<!\w){word}(?!\w)"


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
        """The lines of a file's bytes; a final line feed ends the last line rather than starting an empty one."""
        lines = content.split(LINE_END)
        if not lines[-1]:
            lines.pop()
        starts = list(accumulate((len(line) + len(LINE_END) for line in lines), initial=0))
        return cls(content=content, lines=lines, starts=starts)

    def text(self, line: int) -> str:
        return self.lines[line - FIRST_LINE].decode(TEXT_ENCODING, errors=NOT_TEXT)

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
    """A file's code as its grammar read it: the tree, and the stretches of the file that are code."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    root: Node
    grammar: Grammar
    # The stretches of the file the grammar read; None where it read the whole file
    stretches: list[Range] | None

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
    code = _read_code(code_files_of(path), content)
    named = [] if code is None else _named_places(path, source, code, name, added_lines)
    texts = _text_places(path, source, code, name, added_lines)
    return sorted([*named, *texts], key=lambda place: (place.line, place.column))


def _name_at(path: str, source: SourceLines, position: LinePosition) -> str | None:
    """The name the file's grammar reads at a character, if the character is code and a name's."""
    code = _read_code(code_files_of(path), source.content)
    start = source.offset_of(position)
    if code is None or not code.holds(start):
        return None
    character = source.text(position.line)[position.column]
    name = code.name_around(start, start + len(character.encode(TEXT_ENCODING)))
    return None if name is None else _text_of(name)


def _read_code(files: CodeFiles | None, content: bytes) -> ReadCode | None:
    """A file's code read by its grammar; None for a file of no grammar here, or none of whose stretches is code."""
    if files is None:
        return None
    if files.embedded_in is None:
        root = Parser(files.grammar.language).parse(content).root_node
        return ReadCode(root=root, grammar=files.grammar, stretches=None)
    stretches = _stretches(files.embedded_in, content)
    if not stretches:
        return None
    root = Parser(files.grammar.language, included_ranges=stretches).parse(content).root_node
    return ReadCode(root=root, grammar=files.grammar, stretches=stretches)


def _stretches(embedded: EmbeddedCode, content: bytes) -> list[Range]:
    """The stretches of a file that hold its code, in the order of the file."""
    root = Parser(embedded.language).parse(content).root_node
    captured = QueryCursor(embedded.stretches).captures(root).get(CODE_CAPTURE, [])
    return [node.range for node in sorted(captured, key=lambda node: node.start_byte)]


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
        definition = _definition_of(captures)
        definitions.setdefault(definition.name_start, definition)
    return definitions


def _definition_of(captures: dict[str, list[Node]]) -> Definition:
    """The definition one match of a query captures: the name, and the node of the definition under its kind."""
    [name] = captures[NAME_CAPTURE]
    [kind] = [capture for capture in captures if capture.startswith(DEFINITION_CAPTURE)]
    [defined] = captures[kind]
    return Definition(
        name=_text_of(name),
        kind=DefinitionKind(kind.removeprefix(DEFINITION_CAPTURE)),
        name_start=name.start_byte,
        start=defined.start_byte,
        end=defined.end_byte,
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


def _text_of(node: Node) -> str:
    """What a node of a tree parsed from bytes reads."""
    return (node.text or b"").decode(TEXT_ENCODING, errors=NOT_TEXT)
