"""The languages the review reads names in: a row of data each, so a language is added by adding a row.

A row says which files are of the language, the grammar that reads them,
which of its nodes are names, and a query of what defines one. Each
definition the query captures is `@definition.<kind>`, its kind one of
`DefinitionKind`, with the name it defines captured as `@name`; where two
patterns capture one name, the one written first says what it defines. A
file of no row is read as text.
"""

from pathlib import PurePosixPath

import tree_sitter_javascript
import tree_sitter_python
import tree_sitter_svelte
import tree_sitter_typescript
from pydantic import BaseModel, ConfigDict
from tree_sitter import Language, Query

# What a query of definitions captures a definition as, before its kind, and the name it defines as
DEFINITION_CAPTURE = "definition."
NAME_CAPTURE = "name"
# What a query of where code stands in a file of another language captures each stretch of code as
CODE_CAPTURE = "code"


class Grammar(BaseModel):
    """What reads code of one language: the grammar, which of its nodes are names, and what defines one."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    language: Language
    names: frozenset[str]
    definitions: Query


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

PYTHON_DEFINITIONS = """
(class_definition body: (block (function_definition name: (identifier) @name) @definition.method))
(class_definition
  body: (block (decorated_definition definition: (function_definition name: (identifier) @name) @definition.method)))
(function_definition name: (identifier) @name) @definition.function
(class_definition name: (identifier) @name) @definition.class
(type_alias_statement left: (type (identifier) @name)) @definition.type
(class_definition body: (block (expression_statement (assignment left: (identifier) @name) @definition.field)))
(module (expression_statement (assignment left: (identifier) @name) @definition.variable))
"""

# What JavaScript and TypeScript define alike: a function however written, a method, and a value a program's top
# level names, each declared or destructured, exported or not
SCRIPT_DEFINITIONS = """
(function_declaration name: (identifier) @name) @definition.function
(generator_function_declaration name: (identifier) @name) @definition.function
(variable_declarator name: (identifier) @name value: [(arrow_function) (function_expression)]) @definition.function
(method_definition name: [(property_identifier) (private_property_identifier)] @name) @definition.method
(program
  [(lexical_declaration (variable_declarator name: (identifier) @name) @definition.variable)
   (variable_declaration (variable_declarator name: (identifier) @name) @definition.variable)
   (export_statement
     declaration: (lexical_declaration (variable_declarator name: (identifier) @name) @definition.variable))])
(program
  (lexical_declaration
    (variable_declarator
      name: (object_pattern
        [(shorthand_property_identifier_pattern) @name
         (object_assignment_pattern left: (shorthand_property_identifier_pattern) @name)])) @definition.variable))
"""

JAVASCRIPT_DEFINITIONS = f"""
{SCRIPT_DEFINITIONS}
(class_declaration name: (identifier) @name) @definition.class
(field_definition property: [(property_identifier) (private_property_identifier)] @name) @definition.field
"""

TYPESCRIPT_DEFINITIONS = f"""
{SCRIPT_DEFINITIONS}
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

PYTHON = Grammar(language=PYTHON_LANGUAGE, names=PYTHON_NAMES, definitions=Query(PYTHON_LANGUAGE, PYTHON_DEFINITIONS))
JAVASCRIPT = Grammar(
    language=JAVASCRIPT_LANGUAGE,
    names=JAVASCRIPT_NAMES,
    definitions=Query(JAVASCRIPT_LANGUAGE, JAVASCRIPT_DEFINITIONS),
)
TYPESCRIPT = Grammar(
    language=TYPESCRIPT_LANGUAGE,
    names=TYPESCRIPT_NAMES,
    definitions=Query(TYPESCRIPT_LANGUAGE, TYPESCRIPT_DEFINITIONS),
)
TSX = Grammar(language=TSX_LANGUAGE, names=TYPESCRIPT_NAMES, definitions=Query(TSX_LANGUAGE, TYPESCRIPT_DEFINITIONS))

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
    return CODE_FILES_BY_EXTENSION.get(PurePosixPath(path).suffix)
