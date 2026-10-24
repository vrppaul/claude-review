"""The check that every union of the API requires its label in each branch.

Run as the hook runs it: a process, an OpenAPI document on its stdin.
"""

import subprocess
import sys
from pathlib import Path
from string import Template

CHECK = Path(__file__).parents[2] / "scripts" / "check_union_labels.py"
# What the check exits with: a label left out, or every one required
LABEL_LEFT_OUT = 1
EVERY_LABEL_REQUIRED = 0

# A document with one union of two branches, told apart by `kind`: the line's branch requires what it is given
DOCUMENT = Template("""{
  "components": {
    "schemas": {
      "Anchor": {
        "oneOf": [{"$$ref": "#/components/schemas/LineAnchor"}, {"$$ref": "#/components/schemas/StoryAnchor"}],
        "discriminator": {
          "propertyName": "kind",
          "mapping": {"line": "#/components/schemas/LineAnchor", "story": "#/components/schemas/StoryAnchor"}
        }
      },
      "LineAnchor": {"type": "object", "required": $line_requires},
      "StoryAnchor": {"type": "object", "required": ["kind", "block"]}
    }
  }
}""")
# What the line's branch requires, with its label and without it
WITH_THE_LABEL = '["kind", "file"]'
WITHOUT_THE_LABEL = '["file"]'
# What the check says of a branch that leaves its label out
LINE_LEAVES_IT_OUT = "LineAnchor: does not require `kind`, the label of a union it is a branch of: give the label no default in its schema"


def _checked(line_requires: str) -> subprocess.CompletedProcess[str]:
    """Run the check on the document, its line's branch requiring this."""
    return subprocess.run(
        [sys.executable, str(CHECK)],
        input=DOCUMENT.substitute(line_requires=line_requires),
        capture_output=True,
        text=True,
        check=False,
    )


def test_a_branch_that_leaves_its_unions_label_out_is_named_and_refused() -> None:
    checked = _checked(WITHOUT_THE_LABEL)

    assert checked.stdout.splitlines() == [LINE_LEAVES_IT_OUT]
    assert checked.returncode == LABEL_LEFT_OUT


def test_a_document_whose_every_branch_requires_its_label_passes_unsaid() -> None:
    checked = _checked(WITH_THE_LABEL)

    assert checked.stdout == ""
    assert checked.returncode == EVERY_LABEL_REQUIRED
