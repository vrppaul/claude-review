"""What the browser tests of a fold ask of the page: which way its chevron points, a file's and a thread's alike."""

# The chevron a fold's toggle draws, and the property that turns it from pointing down; the browser turns it
# over a moment, so a test waits for where it comes to rest
CHEVRON = "svg"
TURN = "rotate"
# Pointing down, as a fold does while what it folds is away: pressed, it opens below
POINTING_DOWN = "none"
# Pointing up, as it does while what it folds is open: pressed, it folds up
POINTING_UP = "180deg"
# Whether the chevron of a row that folds what is under it stands at the row's far end, within a pixel of what the
# row holds ending there
CHEVRON_AT_THE_END = """(row) => {
    const end = row.getBoundingClientRect().right - parseFloat(getComputedStyle(row).paddingRight);
    return end - row.querySelector('svg').getBoundingClientRect().right < 1;
}"""
