"""What can go wrong hosting a review, kept apart from the server so the command line names it without loading one."""


class ServerStartError(Exception):
    """Raised when the review's server stopped before it ever listened."""


class PortUnavailableError(Exception):
    """Raised when the review server cannot take the requested port."""


class ReviewStoppedError(Exception):
    """Raised when Ctrl+C or `kill` stopped a review before it ever ran."""
