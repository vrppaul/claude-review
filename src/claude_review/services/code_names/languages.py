"""The languages the review reads names in: a row of data each, so a language is added by adding a row.

A row says which files are of the language, the grammar that reads them,
which of its nodes are names, and a query of what defines one. Each
definition the query captures is `@definition.<kind>`, its kind one of
`DefinitionKind`, with the name it defines captured as `@name`; where two
patterns capture one name, the one written first says what it defines. A
file of no row is read as text.
"""

import posixpath
import re

import tree_sitter_javascript
import tree_sitter_python
import tree_sitter_svelte
import tree_sitter_typescript
from pydantic import BaseModel, ConfigDict
from tree_sitter import Language, Query

from claude_review.domain.code_names import OUTLINES, DefinitionKind

# What a query of definitions captures a definition as, before its kind, and the name it defines as
DEFINITION_CAPTURE = "definition."
NAME_CAPTURE = "name"
# The kind a pattern of a query of definitions captures, as written in it
KIND_CAPTURED = re.compile(rf"@{re.escape(DEFINITION_CAPTURE)}(\w+)")
# What a query of where code stands in a file of another language captures each stretch of code as
CODE_CAPTURE = "code"


class Grammar(BaseModel):
    """What reads code of one language: the grammar, which of its nodes are names, and what defines one."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    language: Language
    names: frozenset[str]
    definitions: Query
    # The patterns of `definitions` that can outline a file (`OUTLINES`) alone, written first as there: an outline
    # never reads each parameter and variable of a file, most of what defines a name in it
    outlines: Query
    # The nodes that wrap a definition with its decorators: their lines are the definition's
    wrappers: frozenset[str]
    # The nodes that open a scope of their own: a definition inside none stands at the top of its file
    scopes: frozenset[str]

    @classmethod
    def reading(
        cls,
        language: Language,
        *,
        names: frozenset[str],
        definitions: str,
        wrappers: frozenset[str],
        scopes: frozenset[str],
    ) -> Grammar:
        """A grammar whose queries of definitions are both made from the patterns written."""
        return cls(
            language=language,
            names=names,
            definitions=Query(language, definitions),
            outlines=_outlining(language, definitions),
            wrappers=wrappers,
            scopes=scopes,
        )


class EmbeddedCode(BaseModel):
    """Where code stands in a file of another language: the grammar of the file, and what captures each stretch."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    language: Language
    stretches: Query


class CodeFiles(BaseModel):
    """Files of one language, by the extensions they end in, and how their code is read."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    extensions: frozenset[str]
    grammar: Grammar
    # Where in such a file its code stands; None where the whole file is code
    embedded_in: EmbeddedCode | None


def _outlining(language: Language, definitions: str) -> Query:
    """A query of these definitions with every pattern of a kind that outlines no file disabled."""
    query = Query(language, definitions)
    written = definitions.encode()
    for pattern in range(query.pattern_count):
        pattern_text = written[query.start_byte_for_pattern(pattern) : query.end_byte_for_pattern(pattern)]
        kinds = {DefinitionKind(kind) for kind in KIND_CAPTURED.findall(pattern_text.decode())}
        if kinds.isdisjoint(OUTLINES):
            query.disable_pattern(pattern)
    return query


PYTHON_LANGUAGE = Language(tree_sitter_python.language())
JAVASCRIPT_LANGUAGE = Language(tree_sitter_javascript.language())
TYPESCRIPT_LANGUAGE = Language(tree_sitter_typescript.language_typescript())
TSX_LANGUAGE = Language(tree_sitter_typescript.language_tsx())
SVELTE_LANGUAGE = Language(tree_sitter_svelte.language())

PYTHON_NAMES = frozenset({"identifier"})
JAVASCRIPT_NAMES = frozenset(
    {
        "identifier",
        "property_identifier",
        "private_property_identifier",
        "shorthand_property_identifier",
        "shorthand_property_identifier_pattern",
    }
)
TYPESCRIPT_NAMES = JAVASCRIPT_NAMES | {"type_identifier"}

# A loop's target, a `with`'s or a catch's name and an import bind a name too, and are left out: none is
# where a reader looks for what a name is
PYTHON_DEFINITIONS = """
(class_definition body: (block (function_definition name: (identifier) @name) @definition.method))
(class_definition
  body: (block (decorated_definition definition: (function_definition name: (identifier) @name) @definition.method)))
(function_definition name: (identifier) @name) @definition.function
(class_definition name: (identifier) @name) @definition.class
(type_alias_statement left: (type (identifier) @name)) @definition.type
(class_definition body: (block (expression_statement (assignment left: (identifier) @name) @definition.field)))
((assignment left: (attribute object: (identifier) @receiver attribute: (identifier) @name)) @definition.field
  (#eq? @receiver "self"))
[(parameters (identifier) @name @definition.parameter)
 (lambda_parameters (identifier) @name @definition.parameter)]
[(default_parameter name: (identifier) @name)
 (typed_default_parameter name: (identifier) @name)] @definition.parameter
(typed_parameter
  [(identifier) @name
   (list_splat_pattern (identifier) @name)
   (dictionary_splat_pattern (identifier) @name)]) @definition.parameter
(parameters
  [(list_splat_pattern (identifier) @name) (dictionary_splat_pattern (identifier) @name)] @definition.parameter)
(assignment left: (identifier) @name) @definition.variable
(assignment left: [(pattern_list (identifier) @name) (tuple_pattern (identifier) @name)]) @definition.variable
(named_expression name: (identifier) @name) @definition.variable
"""

# The names a destructuring pattern binds, in JavaScript and TypeScript alike
DESTRUCTURED_NAMES = """[
  (object_pattern
    [(shorthand_property_identifier_pattern) @name
     (object_assignment_pattern left: (shorthand_property_identifier_pattern) @name)
     (pair_pattern value: (identifier) @name)])
  (array_pattern (identifier) @name)]"""

# What JavaScript and TypeScript define alike: a function however written, a method, a value declared or
# destructured in any scope, and a parameter of an arrow function that takes one bare. A loop's target, a catch's
# name and an import are left out, as in Python
SCRIPT_DEFINITIONS = f"""
(function_declaration name: (identifier) @name) @definition.function
(generator_function_declaration name: (identifier) @name) @definition.function
(variable_declarator name: (identifier) @name value: [(arrow_function) (function_expression)]) @definition.function
(method_definition name: [(property_identifier) (private_property_identifier)] @name) @definition.method
(variable_declarator name: (identifier) @name) @definition.variable
(variable_declarator name: {DESTRUCTURED_NAMES}) @definition.variable
(arrow_function parameter: (identifier) @name @definition.parameter)
"""

JAVASCRIPT_DEFINITIONS = f"""
{SCRIPT_DEFINITIONS}
(class_declaration name: (identifier) @name) @definition.class
(field_definition property: [(property_identifier) (private_property_identifier)] @name) @definition.field
(formal_parameters
  [(identifier) @name
   (assignment_pattern left: (identifier) @name)
   (rest_pattern (identifier) @name)
   {DESTRUCTURED_NAMES}] @definition.parameter)
"""

# What a TypeScript parameter binds, whatever its type or default
TYPESCRIPT_PARAMETER_NAMES = f"[(identifier) @name (rest_pattern (identifier) @name) {DESTRUCTURED_NAMES}]"

TYPESCRIPT_DEFINITIONS = f"""
{SCRIPT_DEFINITIONS}
(function_signature name: (identifier) @name) @definition.function
(required_parameter pattern: {TYPESCRIPT_PARAMETER_NAMES}) @definition.parameter
(optional_parameter pattern: {TYPESCRIPT_PARAMETER_NAMES}) @definition.parameter
(method_signature name: (property_identifier) @name) @definition.method
(abstract_method_signature name: (property_identifier) @name) @definition.method
(class_declaration name: (type_identifier) @name) @definition.class
(abstract_class_declaration name: (type_identifier) @name) @definition.class
(interface_declaration name: (type_identifier) @name) @definition.interface
(type_alias_declaration name: (type_identifier) @name) @definition.type
(enum_declaration name: (identifier) @name) @definition.enum
(public_field_definition name: [(property_identifier) (private_property_identifier)] @name) @definition.field
(property_signature name: (property_identifier) @name) @definition.field
"""

# Where a Svelte component's code stands: in its script elements, the module's and the instance's
SVELTE_SCRIPTS = f"(script_element (raw_text) @{CODE_CAPTURE})"

# What holds a definition with its decorators: Python's decorated definition, and a script's export, which
# holds the decorators written before `export`
PYTHON_WRAPPERS = frozenset({"decorated_definition"})
SCRIPT_WRAPPERS = frozenset({"export_statement"})

# What opens a scope of its own, as a grammar's `locals.scm` marks `@local.scope`: a function of any form, a
# class's body, and in TypeScript a namespace. A block of an `if` or a `try` does not
PYTHON_SCOPES = frozenset({"function_definition", "class_definition"})
SCRIPT_SCOPES = frozenset(
    {
        "function_declaration",
        "generator_function_declaration",
        "function_expression",
        "generator_function",
        "arrow_function",
        "method_definition",
        "class_body",
    }
)
TYPESCRIPT_SCOPES = SCRIPT_SCOPES | {"internal_module", "module"}

PYTHON = Grammar.reading(
    PYTHON_LANGUAGE,
    names=PYTHON_NAMES,
    definitions=PYTHON_DEFINITIONS,
    wrappers=PYTHON_WRAPPERS,
    scopes=PYTHON_SCOPES,
)
JAVASCRIPT = Grammar.reading(
    JAVASCRIPT_LANGUAGE,
    names=JAVASCRIPT_NAMES,
    definitions=JAVASCRIPT_DEFINITIONS,
    wrappers=SCRIPT_WRAPPERS,
    scopes=SCRIPT_SCOPES,
)
TYPESCRIPT = Grammar.reading(
    TYPESCRIPT_LANGUAGE,
    names=TYPESCRIPT_NAMES,
    definitions=TYPESCRIPT_DEFINITIONS,
    wrappers=SCRIPT_WRAPPERS,
    scopes=TYPESCRIPT_SCOPES,
)
TSX = Grammar.reading(
    TSX_LANGUAGE,
    names=TYPESCRIPT_NAMES,
    definitions=TYPESCRIPT_DEFINITIONS,
    wrappers=SCRIPT_WRAPPERS,
    scopes=TYPESCRIPT_SCOPES,
)

# A Svelte component's scripts are read as TypeScript, which reads plain JavaScript as well
CODE_FILES = [
    CodeFiles(extensions=frozenset({".py", ".pyi"}), grammar=PYTHON, embedded_in=None),
    CodeFiles(extensions=frozenset({".js", ".mjs", ".cjs", ".jsx"}), grammar=JAVASCRIPT, embedded_in=None),
    CodeFiles(extensions=frozenset({".ts", ".mts", ".cts"}), grammar=TYPESCRIPT, embedded_in=None),
    CodeFiles(extensions=frozenset({".tsx"}), grammar=TSX, embedded_in=None),
    CodeFiles(
        extensions=frozenset({".svelte"}),
        grammar=TYPESCRIPT,
        embedded_in=EmbeddedCode(language=SVELTE_LANGUAGE, stretches=Query(SVELTE_LANGUAGE, SVELTE_SCRIPTS)),
    ),
]
CODE_FILES_BY_EXTENSION = {extension: files for files in CODE_FILES for extension in files.extensions}


def code_files_of(path: str) -> CodeFiles | None:
    """How a file of this path is read as code: None for a file of no grammar here, read as text."""
    return CODE_FILES_BY_EXTENSION.get(extension_of(path))


def extension_of(path: str) -> str:
    """The extension a path ends in, as its language is told by: none for a name starting with its only dot.

    Split as text: a review asks it of every file of a large tree, and a path object takes many times longer.
    """
    return posixpath.splitext(path)[1]
