"""Domain exceptions for claude-review.

Everything the review refuses is a `ReviewError` of one of five kinds, and
the kind is what whoever asked is told: what they named is not here, what
they asked for no review could serve, what they sent is not acceptable,
or too large, or at odds with where the review stands. The specific error
says why, in words the asker can act on.

A refusal says one thing wrong. What is sent whole and read whole — a
document — may be wrong in many places at once, and whoever sent it should
not learn of them one refusal at a time: such a refusal carries every fault
found, each at the field it is about.
"""

from pydantic import BaseModel, ConfigDict


class ReviewError(Exception):
    """Raised when the review will not do what it was asked; the message says why."""


class NotFoundError(ReviewError):
    """Raised when what a request names is not in this review."""


class InvalidRequestError(ReviewError):
    """Raised when a request asks for something no review could serve."""


class RefusedError(ReviewError):
    """Raised when a request is understood, and what it carries is not acceptable."""


class TooLargeError(RefusedError):
    """Raised when what a request carries is more than the review takes."""


class ConflictError(ReviewError):
    """Raised when a request is at odds with where the review already stands."""


# Where a field stands in what was sent: the names and positions that lead to
# it, as the JSON it came in nests them
type FieldPath = tuple[str | int, ...]


class FieldFault(BaseModel):
    """One thing wrong with what was sent: the field it is about, and what is wrong there."""

    model_config = ConfigDict(frozen=True)

    path: FieldPath
    reason: str


class FieldsRefusedError(RefusedError):
    """Raised when what a request carries is wrong field by field; it carries every fault found, not the first."""

    def __init__(self, message: str, faults: list[FieldFault]) -> None:
        super().__init__(message)
        self.faults = faults


class NoRepositoryError(NotFoundError):
    """Raised when a review whose content did not come from a repository is asked for git's help."""


class QuestionNotInThreadError(RefusedError):
    """Raised when a question names neither its thread's opening nor a turn the reader wrote in it."""


class UnknownThreadError(NotFoundError):
    """Raised when a thread is named that the review does not hold."""


class AgentWordsChangedError(RefusedError):
    """Raised when a thread the agent raised comes back no longer opening as the agent raised it."""


class ReviewEndedError(ConflictError):
    """Raised when a review that has ended is sent more."""


class LineRangeError(InvalidRequestError):
    """Raised when lines are asked for that no file could have: a range that runs backwards."""


class PathOutsideRepositoryError(InvalidRequestError):
    """Raised when a path is not one inside the repository under review."""


class FileNotInReviewError(NotFoundError):
    """Raised when a file is asked for that the review neither holds nor tracks, or that is not there."""


class FileUnreadableError(RefusedError):
    """Raised when a file the review holds cannot be read as text, or is too large to read."""


class UnknownVersionError(InvalidRequestError):
    """Raised when a base is asked for that this review never offered."""


class UnknownAnchorFileError(NotFoundError):
    """Raised when an anchor names a file this review does not hold."""


class UnknownFileError(NotFoundError):
    """Raised when the reader is to be taken to a file this review does not hold."""


class AnchorTooLongError(RefusedError):
    """Raised when an anchor names more lines than a thread may quote."""


class AnchorLinesNotShownError(RefusedError):
    """Raised when an anchor names lines of a file that the diff does not show."""


class ImageRefusedError(RefusedError):
    """Raised when an upload is not an image this review can keep."""


class ImageTooLargeError(TooLargeError):
    """Raised when an upload would take an image, or the review, past its limit."""


class ImagesNotKeptError(RefusedError):
    """Raised when something sent names images this review does not keep."""


class UnknownImageError(NotFoundError):
    """Raised when an image is asked for that this review does not keep."""


class ImageAlreadySentError(ConflictError):
    """Raised when an image that went out with a message is asked to be removed."""


class StoryRefusedError(FieldsRefusedError):
    """Raised when a story may not be told as it was written."""
