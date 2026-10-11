"""Text the reader or the code under review wrote, made safe to print where a terminal reads it.

A file name, a quoted line or a comment can hold the terminal's own
controls: a sequence that clears the screen, retitles the window, or — OSC
52 — writes the clipboard. Printed as it stands, what is under review would
be talking to the terminal of whoever reads it. Every control character
but the new line, the tab and a line's own carriage return is written out
instead, as JSON escapes one: visible to a person, and the same string again
to a program reading JSON.
"""

import re

# The characters a terminal may act on rather than show: C0, and DEL with C1
C0_CONTROLS = range(0x20)
DELETE_AND_C1_CONTROLS = range(0x7F, 0xA0)
# What text means a terminal to act on: a new line, a tab, and a carriage
# return — which ends a line only when a new line follows it, as every line
# of a file written on Windows ends
CARRIAGE_RETURN = "\r"
MEANT_FOR_THE_TERMINAL = frozenset(f"\n\t{CARRIAGE_RETURN}")
# How a control is written out where it stood
WRITTEN_OUT = "\\u{code:04x}"

# Every control a terminal would act on, by its code, and what is printed instead
CONTROLS_WRITTEN_OUT = {
    code: WRITTEN_OUT.format(code=code)
    for code in (*C0_CONTROLS, *DELETE_AND_C1_CONTROLS)
    if chr(code) not in MEANT_FOR_THE_TERMINAL
}
# A carriage return that ends no line sends the cursor back to write over
# what was printed, so what is shown is not what is there: it is written out
OVERWRITING_RETURN = re.compile(f"{CARRIAGE_RETURN}(?!\n)")
RETURN_WRITTEN_OUT = WRITTEN_OUT.format(code=ord(CARRIAGE_RETURN))


def terminal_text(text: str) -> str:
    """The text with every control a terminal would act on written out where it stood."""
    # A function, not a replacement string: the regex would read the backslash of `\u` as its own
    return OVERWRITING_RETURN.sub(lambda _: RETURN_WRITTEN_OUT, text.translate(CONTROLS_WRITTEN_OUT))
