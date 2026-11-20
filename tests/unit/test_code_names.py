"""Functional requirement tests for what a name is in each language the review reads, and where one stands in a file.

The grammar decides: a word a comment, a string or the language holds is no
name, and a file of no grammar is read as text, a line to each place.
"""

import pytest

from claude_review.domain.code_names import DefinitionKind, FoundAs, NamePlace
from claude_review.domain.exceptions import NoWordHereError
from claude_review.services.code_names.reading import places_of, word_at

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
    ("line", "column"),
    [(12, 21), (3, 5), (17, 0), (99, 0), (12, 99)],
    ids=["punctuation", "a-blank", "past-the-last-line", "far-past-the-end", "past-the-line-end"],
)
def test_a_place_that_holds_no_word_is_refused(line: int, column: int) -> None:
    with pytest.raises(NoWordHereError):
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
