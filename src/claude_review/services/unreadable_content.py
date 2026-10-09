"""What goes wrong reading what was asked to be reviewed, said so the command line can name it in a line."""


class UnreadableContentError(Exception):
    """Raised when what was asked to be reviewed cannot be read: a file missing or not text, a transcript not JSON."""
