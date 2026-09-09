"""Domain exceptions for claude-review."""


class GitError(Exception):
    """Raised when a git operation fails."""


class PortUnavailableError(Exception):
    """Raised when the review server cannot take the requested port."""


class FileWindowError(Exception):
    """Raised when a requested window of file content cannot be served."""
