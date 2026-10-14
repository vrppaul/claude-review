"""What the browser tests of the line keys ask of the page, of the files and of a story alike."""

# The keys that step a line down and up
LINE_KEYS = ("j", "k")
# How far down an area has scrolled, in pixels
SCROLLED = "(area) => area.scrollTop"
# How far under the foot of a header the line that holds the keyboard begins, in heights of a line: under 0
# the header is drawn over it, and from 1 on a line above it is in sight too. Asked of the header kept in sight
LINES_UNDER_THE_HEADER = """(header) => {
    const line = document.activeElement;
    const under = line.getBoundingClientRect().top - header.getBoundingClientRect().bottom;
    return under / line.getBoundingClientRect().height;
}"""
# A fraction of a line: where an edge stands is not a whole number of pixels
LESS_THAN_A_LINE_APART = 0.05
