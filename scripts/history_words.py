"""The words that tell what the code was, where prose says what stands (`.claude/rules/prose.md`).

Two gates refuse them: the one on the comments and docstrings of Python files, and the one on a commit's message.
"""

import re

# `no longer than` bounds a wait or a size, and tells nothing of what was. A file renamed is what a diff shows,
# so a rename is refused only where it names the other name
TOLD_AS_HISTORY = re.compile(
    r"\b("
    r"no longer(?! than)|anymore|formerly|the old way|used to be"
    r"|(?:was|were|has been|have been) renamed to|renamed from|was changed to"
    r"|now uses"
    r")\b",
    re.IGNORECASE,
)
