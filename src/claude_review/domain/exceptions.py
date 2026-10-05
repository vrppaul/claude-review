"""Domain exceptions for claude-review."""


class GitError(Exception):
    """Raised when a git operation fails."""


class PortUnavailableError(Exception):
    """Raised when the review server cannot take the requested port."""


class FileWindowError(Exception):
    """Raised when a requested window of file content cannot be served."""


class UnknownVersionError(Exception):
    """Raised when a base is asked for that this review never offered."""


class ImageRefusedError(Exception):
    """Raised when an upload is not an image this review can keep."""


class ImageTooLargeError(ImageRefusedError):
    """Raised when an upload would take an image, or the review, past its limit."""


class UnknownImageError(Exception):
    """Raised when an image is named that this review does not keep."""


class ImageAlreadySentError(Exception):
    """Raised when an image that went out with a message is asked to be removed."""
