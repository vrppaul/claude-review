"""Where a browser test puts a control before it acts: scrolled to stand just under the header kept in sight.

Setup, never a check: the one place a test reads where a box stands, as the
reader's own scrolling would have left it. The check that no browser test
reads a box (`.pre-commit-config.yaml`) leaves this module alone for that.
"""

# Scroll a reading area by as much as stands a control's top so many pixels under the foot of a header kept
# over it
import os

TOP_UNDER = """(area, [control, header, under]) => {
    area.scrollTop += control.getBoundingClientRect().top - (header.getBoundingClientRect().bottom + under);
}"""

# PROBE, never merged: the same scroll, waiting two frames for the browser to draw what it brought near
if os.environ.get("PROBE_SETTLE"):
    TOP_UNDER = """(area, [control, header, under]) => {
    area.scrollTop += control.getBoundingClientRect().top - (header.getBoundingClientRect().bottom + under);
    return new Promise((drawn) => requestAnimationFrame(() => requestAnimationFrame(drawn)));
}"""
