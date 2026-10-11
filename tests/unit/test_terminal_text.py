"""What the code under review wrote, printed where a terminal reads it: shown, never obeyed."""

import json
import unicodedata

import pytest

from claude_review.cli.terminal_text import terminal_text

ESCAPE = "\x1b"
BELL = "\x07"
# Writes "echo pwned" into the clipboard of the terminal that prints it (OSC 52)
CLIPBOARD_WRITE = f"{ESCAPE}]52;c;ZWNobyBwd25lZA=={BELL}"
# Clears the screen (CSI), and the same as one C1 control, the 8-bit CSI
CLEAR_SCREEN = f"{ESCAPE}[2J"
C1_CLEAR_SCREEN = "\x9b2J"
# Moves back to the start of the line, so what follows is written over what came before
CARRIAGE_RETURN = "\r"
# Switches the terminal to another character set until switched back
SHIFT_OUT = "\x0e"
DELETE = "\x7f"
# Unicode's category for a control character: C0, DEL and C1 alike
CONTROL_CATEGORY = "Cc"
# What a terminal is meant to act on in text: a new line, a tab
MEANT = "\n\t"


def _controls_in(printed: str) -> list[str]:
    """Every control character a terminal would act on, other than a new line or a tab."""
    return [
        character
        for character in printed
        if unicodedata.category(character) == CONTROL_CATEGORY and character not in MEANT
    ]


@pytest.mark.parametrize(
    "hostile",
    [CLIPBOARD_WRITE, CLEAR_SCREEN, C1_CLEAR_SCREEN, CARRIAGE_RETURN, SHIFT_OUT, DELETE],
    ids=["osc-52", "csi", "c1-csi", "carriage-return", "shift-out", "delete"],
)
def test_nothing_the_text_holds_reaches_the_terminal_as_a_control(hostile: str) -> None:
    assert _controls_in(terminal_text(f"before {hostile} after")) == []


def test_a_control_is_shown_where_it_stood() -> None:
    """Visible, so whoever reads it sees that the file holds one, and where."""
    assert terminal_text(f"x{CLEAR_SCREEN}y") == "x\\u001b[2Jy"


def test_lines_tabs_and_every_language_are_left_as_they_are() -> None:
    text = "def greet():\n\treturn 'Готово — “done” 🙂'"

    assert terminal_text(text) == text


def test_json_made_safe_reads_back_as_it_was() -> None:
    """The agent's commands print JSON for a program to read: made safe, it says the same."""
    said = {"body": f"{C1_CLEAR_SCREEN} {CLIPBOARD_WRITE} {DELETE}"}

    printed = terminal_text(json.dumps(said, ensure_ascii=False))

    assert json.loads(printed) == said


def test_a_line_ended_as_windows_ends_it_is_kept() -> None:
    """A carriage return before a new line only ends the line, as every line of a file written on Windows ends."""
    text = "first line\r\nsecond line\r\n"

    assert terminal_text(text) == text


def test_a_carriage_return_that_ends_no_line_is_shown() -> None:
    """Alone, it sends the cursor back to write over what was printed: what is shown is not what is there."""
    assert terminal_text("rm -rf ~\rls\r\n") == "rm -rf ~\\u000dls\r\n"
