"""What can go wrong hosting a review, kept apart from the server so the command line names it without loading one."""


class ServerStartError(Exception):
    """Raised when the review's server stopped before it ever listened."""
