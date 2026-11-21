"""Functional requirement tests for what a name is in each language the review reads, and where one stands in a file.

The grammar decides: a word a comment, a string or the language holds is no
name, and a file of no grammar is read as text, a line to each place. It
decides too which names outline a file: those standing at its top.
"""

import pytest

from claude_review.domain.code_names import DefinitionKind, FoundAs, NamePlace
from claude_review.domain.exceptions import NoWordHereError
from claude_review.domain.models import LineSpan
from claude_review.services.code_names import reading
from claude_review.services.code_names.reading import LinePosition, OutlinedName, outline, places_of, word_at

PYTHON_FILE = b'''"""Reviews and their lookup."""

LIMIT = 3


class Review:
    title: str = "lookup"

    @property
    def lookup(self) -> int:
        # lookup stays a word here
        return lookup(LIMIT)


def lookup(limit: int) -> int:
    return limit
'''

TYPESCRIPT_FILE = b"""export interface Shown {
  shown: boolean;
  show(): void;
}

export type Showing = Shown | null;

export class Pane implements Shown {
  shown = false;
  show(): void {
    this.shown = true;
  }
}

export enum Side { Old, New }
"""

JAVASCRIPT_FILE = b"""export class Drawer {
  #open = false;
  toggle() {}
}

export const drawn = () => new Drawer();
"""

PYTHON_BINDINGS = b"""import os


class Store:
    def __init__(self, objects: str, *paths: str, limit=2) -> None:
        self._objects = objects
        reader = lambda named: named
        reader.size = limit
        first, rest = paths[0], paths[1:]
        if (count := len(rest)) > limit:
            total = count

    def entries(self) -> None:
        for entry in os.listdir(self._objects):
            with open(entry) as handle:
                try:
                    handle.read()
                except OSError as failure:
                    raise failure
"""

TYPESCRIPT_BINDINGS = b"""import { Size } from './size';

export function draw(width: number, { height }: Size, depth?: number, ...rest: number[]): number {
  const area = width * height;
  let [first] = rest;
  const scaled = (factor: number) => area * factor;
  const doubled = rest.map(item => item * 2);
  for (const each of rest) {
    try {
      scaled(each);
    } catch (problem) {
      throw problem;
    }
  }
  return first;
}
"""

JAVASCRIPT_BINDINGS = b"""export function drawn(width, { height }, depth = 1, ...rest) {
  const [first] = rest;
  return width * height * depth * first;
}
"""

SVELTE_FILE = b"""<script lang="ts">
  let { open = false } = $props();
  const shown = $derived(open);
</script>

{#if open}<p class="open">{shown}</p>{/if}
"""

TEXT_FILE = b"""The lookup reads a name.
lookup, lookup and lookups
nothing here
"""


@pytest.mark.parametrize(
    ("path", "content", "line", "column", "word"),
    [
        ("review.py", PYTHON_FILE, 12, 16, "lookup"),
        ("review.py", PYTHON_FILE, 11, 12, "lookup"),
        ("review.py", PYTHON_FILE, 7, 19, "lookup"),
        ("review.py", PYTHON_FILE, 15, 1, "def"),
        ("pane.ts", TYPESCRIPT_FILE, 6, 22, "Shown"),
        ("Pane.svelte", SVELTE_FILE, 2, 9, "open"),
        ("Pane.svelte", SVELTE_FILE, 2, 25, "$props"),
        ("Pane.svelte", SVELTE_FILE, 6, 7, "open"),
        ("notes.md", TEXT_FILE, 1, 6, "lookup"),
    ],
    ids=[
        "a-name",
        "a-comment-word",
        "a-string-word",
        "a-keyword",
        "a-type-name",
        "a-svelte-script-name",
        "a-name-of-a-rune",
        "a-word-of-svelte-markup",
        "a-word-of-a-file-of-no-grammar",
    ],
)
def test_the_word_at_a_place_is_the_name_the_grammar_reads_there_or_the_word_of_text_it_stands_in(
    path: str, content: bytes, line: int, column: int, word: str
) -> None:
    assert word_at(path, content, line, column) == word


@pytest.mark.parametrize(
    ("line", "column", "said"),
    [
        (12, 21, "line 12, column 21 of review.py holds no word"),
        (3, 5, "line 3, column 5 of review.py holds no word"),
        (2, 0, "line 2, column 0 of review.py holds no word"),
        (12, 28, "line 12, column 28 of review.py holds no word"),
        (12, 29, "line 12 of review.py has no column 29"),
        (17, 0, "review.py has no line 17"),
    ],
    ids=["punctuation", "a-blank", "a-blank-line", "the-line-end", "past-the-line-end", "past-the-last-line"],
)
def test_a_place_that_holds_no_word_is_refused_saying_what_is_wrong(line: int, column: int, said: str) -> None:
    with pytest.raises(NoWordHereError, match=f"^{said}$"):
        word_at("review.py", PYTHON_FILE, line, column)


def test_python_names_are_found_where_they_define_and_use_never_in_a_comment_or_a_string() -> None:
    places = places_of("review.py", PYTHON_FILE, "lookup", frozenset({15}))

    assert places == [
        NamePlace(
            path="review.py",
            line=10,
            column=8,
            text="    def lookup(self) -> int:",
            defined_as=DefinitionKind.METHOD,
            inside="Review",
            added=False,
            found_as=FoundAs.NAME,
        ),
        NamePlace(
            path="review.py",
            line=12,
            column=15,
            text="        return lookup(LIMIT)",
            defined_as=None,
            inside="lookup",
            added=False,
            found_as=FoundAs.NAME,
        ),
        NamePlace(
            path="review.py",
            line=15,
            column=4,
            text="def lookup(limit: int) -> int:",
            defined_as=DefinitionKind.FUNCTION,
            inside=None,
            added=True,
            found_as=FoundAs.NAME,
        ),
    ]


@pytest.mark.parametrize(
    ("path", "content", "name", "defined_as"),
    [
        ("review.py", PYTHON_FILE, "Review", DefinitionKind.CLASS),
        ("review.py", PYTHON_FILE, "title", DefinitionKind.FIELD),
        ("review.py", PYTHON_FILE, "LIMIT", DefinitionKind.VARIABLE),
        ("pane.ts", TYPESCRIPT_FILE, "Shown", DefinitionKind.INTERFACE),
        ("pane.ts", TYPESCRIPT_FILE, "Showing", DefinitionKind.TYPE),
        ("pane.ts", TYPESCRIPT_FILE, "Pane", DefinitionKind.CLASS),
        ("pane.ts", TYPESCRIPT_FILE, "Side", DefinitionKind.ENUM),
        ("drawer.js", JAVASCRIPT_FILE, "Drawer", DefinitionKind.CLASS),
        ("drawer.js", JAVASCRIPT_FILE, "#open", DefinitionKind.FIELD),
        ("drawer.js", JAVASCRIPT_FILE, "toggle", DefinitionKind.METHOD),
        ("drawer.js", JAVASCRIPT_FILE, "drawn", DefinitionKind.FUNCTION),
        ("store.py", PYTHON_BINDINGS, "objects", DefinitionKind.PARAMETER),
        ("store.py", PYTHON_BINDINGS, "paths", DefinitionKind.PARAMETER),
        ("store.py", PYTHON_BINDINGS, "limit", DefinitionKind.PARAMETER),
        ("store.py", PYTHON_BINDINGS, "named", DefinitionKind.PARAMETER),
        ("store.py", PYTHON_BINDINGS, "_objects", DefinitionKind.FIELD),
        ("store.py", PYTHON_BINDINGS, "reader", DefinitionKind.VARIABLE),
        ("store.py", PYTHON_BINDINGS, "first", DefinitionKind.VARIABLE),
        ("store.py", PYTHON_BINDINGS, "count", DefinitionKind.VARIABLE),
        ("store.py", PYTHON_BINDINGS, "total", DefinitionKind.VARIABLE),
        ("draw.ts", TYPESCRIPT_BINDINGS, "width", DefinitionKind.PARAMETER),
        ("draw.ts", TYPESCRIPT_BINDINGS, "height", DefinitionKind.PARAMETER),
        ("draw.ts", TYPESCRIPT_BINDINGS, "depth", DefinitionKind.PARAMETER),
        ("draw.ts", TYPESCRIPT_BINDINGS, "rest", DefinitionKind.PARAMETER),
        ("draw.ts", TYPESCRIPT_BINDINGS, "factor", DefinitionKind.PARAMETER),
        ("draw.ts", TYPESCRIPT_BINDINGS, "item", DefinitionKind.PARAMETER),
        ("draw.ts", TYPESCRIPT_BINDINGS, "area", DefinitionKind.VARIABLE),
        ("draw.ts", TYPESCRIPT_BINDINGS, "first", DefinitionKind.VARIABLE),
        ("draw.ts", TYPESCRIPT_BINDINGS, "scaled", DefinitionKind.FUNCTION),
        ("draw.ts", TYPESCRIPT_BINDINGS, "doubled", DefinitionKind.VARIABLE),
        ("drawn.js", JAVASCRIPT_BINDINGS, "width", DefinitionKind.PARAMETER),
        ("drawn.js", JAVASCRIPT_BINDINGS, "height", DefinitionKind.PARAMETER),
        ("drawn.js", JAVASCRIPT_BINDINGS, "depth", DefinitionKind.PARAMETER),
        ("drawn.js", JAVASCRIPT_BINDINGS, "rest", DefinitionKind.PARAMETER),
        ("drawn.js", JAVASCRIPT_BINDINGS, "first", DefinitionKind.VARIABLE),
        ("Pane.svelte", SVELTE_FILE, "open", DefinitionKind.VARIABLE),
        ("Pane.svelte", SVELTE_FILE, "shown", DefinitionKind.VARIABLE),
    ],
)
def test_a_definition_says_what_it_defines(path: str, content: bytes, name: str, defined_as: DefinitionKind) -> None:
    [definition] = [place for place in places_of(path, content, name, frozenset()) if place.defined_as is not None]

    assert definition.defined_as == defined_as


@pytest.mark.parametrize(
    ("path", "content", "name"),
    [
        ("store.py", PYTHON_BINDINGS, "os"),
        ("store.py", PYTHON_BINDINGS, "entry"),
        ("store.py", PYTHON_BINDINGS, "handle"),
        ("store.py", PYTHON_BINDINGS, "failure"),
        ("store.py", PYTHON_BINDINGS, "size"),
        ("draw.ts", TYPESCRIPT_BINDINGS, "Size"),
        ("draw.ts", TYPESCRIPT_BINDINGS, "each"),
        ("draw.ts", TYPESCRIPT_BINDINGS, "problem"),
    ],
)
def test_an_import_a_loop_target_a_with_s_or_a_catch_s_name_and_another_object_s_attribute_define_nothing(
    path: str, content: bytes, name: str
) -> None:
    places = places_of(path, content, name, frozenset())

    assert [place.defined_as for place in places] == [None] * len(places)


def test_a_typescript_member_is_defined_by_the_interface_and_by_the_class_and_used_inside_its_method() -> None:
    places = places_of("pane.ts", TYPESCRIPT_FILE, "shown", frozenset())

    assert [(place.line, place.defined_as, place.inside) for place in places] == [
        (2, DefinitionKind.FIELD, "Shown"),
        (9, DefinitionKind.FIELD, "Pane"),
        (11, None, "show"),
    ]


OVERLOADED = b"""export function over(a: number): number;
export function over(a: unknown): unknown {
  return a;
}
over(1);
"""


def test_a_typescript_overload_s_signature_defines_its_function_and_holds_its_parameter() -> None:
    functions = places_of("over.ts", OVERLOADED, "over", frozenset())
    parameters = places_of("over.ts", OVERLOADED, "a", frozenset())

    assert [(place.line, place.defined_as, place.inside) for place in [*functions, *parameters]] == [
        (1, DefinitionKind.FUNCTION, None),
        (2, DefinitionKind.FUNCTION, None),
        (5, None, None),
        (1, DefinitionKind.PARAMETER, "over"),
        (2, DefinitionKind.PARAMETER, "over"),
        (3, None, "over"),
    ]


def test_a_svelte_name_is_read_in_its_script_and_found_as_text_in_its_markup() -> None:
    places = places_of("Pane.svelte", SVELTE_FILE, "open", frozenset())

    assert [(place.line, place.column, place.found_as) for place in places] == [
        (2, 8, FoundAs.NAME),
        (3, 25, FoundAs.NAME),
        (6, 5, FoundAs.TEXT),
    ]


def test_a_file_of_no_grammar_is_searched_for_the_whole_word_a_line_to_each_place() -> None:
    places = places_of("notes.md", TEXT_FILE, "lookup", frozenset({2}))

    assert places == [
        NamePlace(
            path="notes.md",
            line=1,
            column=4,
            text="The lookup reads a name.",
            defined_as=None,
            inside=None,
            added=False,
            found_as=FoundAs.TEXT,
        ),
        NamePlace(
            path="notes.md",
            line=2,
            column=0,
            text="lookup, lookup and lookups",
            defined_as=None,
            inside=None,
            added=True,
            found_as=FoundAs.TEXT,
        ),
    ]


def test_a_place_stands_inside_what_holds_code_never_inside_a_value() -> None:
    content = b"VISIBLE = shown()\n\n\nclass Pane:\n    shown_at = shown()\n"

    places = places_of("pane.py", content, "shown", frozenset())

    assert [(place.line, place.inside) for place in places] == [(1, None), (5, "Pane")]


def test_a_column_counts_characters_not_bytes() -> None:
    content = "label = 'café'; lookup = 1\n".encode()

    [place] = places_of("labels.py", content, "lookup", frozenset())

    assert (place.column, word_at("labels.py", content, 1, place.column)) == (16, "lookup")


PYTHON_OUTLINED = b"""import os

LIMIT = 3


class Review:
    def lookup(self) -> int:
        return LIMIT


@cache
def shown() -> bool:
    def inner() -> bool:
        return True

    return inner()


type Shown = bool


def untouched() -> None:
    pass
"""

TYPESCRIPT_OUTLINED = b"""export interface Shown {
  shown: boolean;
}

export type Showing = Shown | null;

export enum Side { Old, New }

@Component({})
export class Pane implements Shown {
  shown = false;
  show(): void {
    this.shown = true;
  }
}

export function drawn(width: number): Pane;
export function drawn(width: number, height?: number): Pane {
  const inner = () => new Pane();
  return inner();
}

export const LIMIT = 3;

describe("suite", () => {
  function helperInCallback(): void {}
});

namespace Space {
  export function inNamespace(): void {}
}

if (shown) {
  function insideIf(): void {}
}
"""

JAVASCRIPT_OUTLINED = b"""export class Drawer {
  toggle() {}
}

export const drawn = () => new Drawer();

function* steps() {
  yield 1;
}

(function () {
  function insideIife() {}
})();

onMount(() => {
  class LocalInCallback {}
});
"""

TSX_OUTLINED = b"""export function Pane(): JSX.Element {
  return <p>shown</p>;
}

items.forEach(() => {
  function eachItem(): void {}
});
"""

SVELTE_OUTLINED = b"""<script lang="ts">
  let { open = false } = $props();
  function toggle(): void {
    open = !open;
  }
  $effect(() => {
    function inEffect(): void {}
  });
</script>

{#if open}<p>shown</p>{/if}
"""


@pytest.mark.parametrize(
    ("path", "content", "outlined"),
    [
        (
            "review.py",
            PYTHON_OUTLINED,
            [
                OutlinedName(
                    name="Review",
                    kind=DefinitionKind.CLASS,
                    named_at=LinePosition(line=6, column=6),
                    spans=[LineSpan(first=6, last=8)],
                ),
                OutlinedName(
                    name="shown",
                    kind=DefinitionKind.FUNCTION,
                    named_at=LinePosition(line=12, column=4),
                    spans=[LineSpan(first=11, last=16)],
                ),
                OutlinedName(
                    name="Shown",
                    kind=DefinitionKind.TYPE,
                    named_at=LinePosition(line=19, column=5),
                    spans=[LineSpan(first=19, last=19)],
                ),
                OutlinedName(
                    name="untouched",
                    kind=DefinitionKind.FUNCTION,
                    named_at=LinePosition(line=22, column=4),
                    spans=[LineSpan(first=22, last=23)],
                ),
            ],
        ),
        (
            "pane.ts",
            TYPESCRIPT_OUTLINED,
            [
                OutlinedName(
                    name="Shown",
                    kind=DefinitionKind.INTERFACE,
                    named_at=LinePosition(line=1, column=17),
                    spans=[LineSpan(first=1, last=3)],
                ),
                OutlinedName(
                    name="Showing",
                    kind=DefinitionKind.TYPE,
                    named_at=LinePosition(line=5, column=12),
                    spans=[LineSpan(first=5, last=5)],
                ),
                OutlinedName(
                    name="Side",
                    kind=DefinitionKind.ENUM,
                    named_at=LinePosition(line=7, column=12),
                    spans=[LineSpan(first=7, last=7)],
                ),
                OutlinedName(
                    name="Pane",
                    kind=DefinitionKind.CLASS,
                    named_at=LinePosition(line=10, column=13),
                    spans=[LineSpan(first=9, last=15)],
                ),
                OutlinedName(
                    name="drawn",
                    kind=DefinitionKind.FUNCTION,
                    named_at=LinePosition(line=17, column=16),
                    spans=[LineSpan(first=17, last=17), LineSpan(first=18, last=21)],
                ),
                OutlinedName(
                    name="insideIf",
                    kind=DefinitionKind.FUNCTION,
                    named_at=LinePosition(line=34, column=11),
                    spans=[LineSpan(first=34, last=34)],
                ),
            ],
        ),
        (
            "drawer.js",
            JAVASCRIPT_OUTLINED,
            [
                OutlinedName(
                    name="Drawer",
                    kind=DefinitionKind.CLASS,
                    named_at=LinePosition(line=1, column=13),
                    spans=[LineSpan(first=1, last=3)],
                ),
                OutlinedName(
                    name="drawn",
                    kind=DefinitionKind.FUNCTION,
                    named_at=LinePosition(line=5, column=13),
                    spans=[LineSpan(first=5, last=5)],
                ),
                OutlinedName(
                    name="steps",
                    kind=DefinitionKind.FUNCTION,
                    named_at=LinePosition(line=7, column=10),
                    spans=[LineSpan(first=7, last=9)],
                ),
            ],
        ),
        (
            "Pane.tsx",
            TSX_OUTLINED,
            [
                OutlinedName(
                    name="Pane",
                    kind=DefinitionKind.FUNCTION,
                    named_at=LinePosition(line=1, column=16),
                    spans=[LineSpan(first=1, last=3)],
                )
            ],
        ),
        (
            "Pane.svelte",
            SVELTE_OUTLINED,
            [
                OutlinedName(
                    name="toggle",
                    kind=DefinitionKind.FUNCTION,
                    named_at=LinePosition(line=3, column=11),
                    spans=[LineSpan(first=3, last=5)],
                )
            ],
        ),
        ("notes.md", TEXT_FILE, []),
        (
            "twice.py",
            b"def twice() -> int:\n    return 1\n\n\ndef twice() -> int:\n    return 2\n",
            [
                OutlinedName(
                    name="twice",
                    kind=DefinitionKind.FUNCTION,
                    named_at=LinePosition(line=1, column=4),
                    spans=[LineSpan(first=1, last=2), LineSpan(first=5, last=6)],
                )
            ],
        ),
        (
            "broken.py",
            b"def broken(:\n    pass\n\n\ndef whole() -> int:\n    return 1\n",
            [
                OutlinedName(
                    name="broken",
                    kind=DefinitionKind.FUNCTION,
                    named_at=LinePosition(line=1, column=4),
                    spans=[LineSpan(first=1, last=2)],
                ),
                OutlinedName(
                    name="whole",
                    kind=DefinitionKind.FUNCTION,
                    named_at=LinePosition(line=5, column=4),
                    spans=[LineSpan(first=5, last=6)],
                ),
            ],
        ),
    ],
    ids=[
        "python",
        "typescript",
        "javascript",
        "tsx",
        "svelte",
        "a-file-of-no-grammar",
        "a-name-defined-twice-once-with-the-lines-of-both",
        "a-file-its-grammar-reads-in-part-with-the-names-it-can",
    ],
)
def test_the_names_outlining_a_file_are_those_at_its_top_each_with_every_line_it_is_defined_on(
    path: str, content: bytes, outlined: list[OutlinedName]
) -> None:
    assert outline(path, content) == outlined


# A run of comment lines Python's grammar reads in time that grows with its square: some 0.6 s for these
SLOW_TO_PARSE = b"def big():\n" + b"    # pad\n" * 3000 + b"    pass\n"
# How long the test lets one file's parse take, far shorter than the review's own so the test stays cheap
SHORT_PARSE_SECONDS = 0.01


def test_a_file_whose_parse_takes_too_long_cannot_be_outlined_and_is_looked_through_as_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(reading, "LONGEST_PARSE_SECONDS", SHORT_PARSE_SECONDS)

    places = places_of("big.py", SLOW_TO_PARSE, "big", frozenset())

    assert (outline("big.py", SLOW_TO_PARSE), [place.found_as for place in places]) == (None, [FoundAs.TEXT])
