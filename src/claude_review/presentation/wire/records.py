"""What every review on the machine keeps about its reader, as the page reads and changes it."""

from pydantic import ConfigDict, Field

from claude_review.domain.models import DiffLayout, Theme
from claude_review.presentation.wire.base import WireModel

# A release number, generously: 1.5.0, 1.5.0rc1, 1.4.3.dev0
MAX_RELEASE_LENGTH = 50


class ReaderSettings(WireModel):
    """How this reader reads a review, the same in every review on the machine."""

    theme: Theme
    diff_layout: DiffLayout
    # Leave out changes that only alter whitespace
    ignore_whitespace: bool
    # A tick when an answer arrives while the review is in a background tab
    sound_on_replies: bool


class GuideState(WireModel):
    """What the review remembers of having shown this reader around."""

    # The release whose news the reader was last shown
    seen_release: str | None


class KeptRecord[Record: WireModel](WireModel):
    """One record kept about the reader, and whether anything has been kept at all.

    A reader nothing has been kept about gets the defaults, and is told so:
    a page still holding choices made before they moved to the server hands
    them over once, when nothing is stored.
    """

    record: Record
    stored: bool


class SettingsChange(WireModel):
    """Request body for PUT /api/settings — the choices being changed, and only those.

    A choice sent as null is a choice not sent, as in every change to what
    is kept about the reader.
    """

    model_config = ConfigDict(extra="forbid")

    theme: Theme | None = None
    diff_layout: DiffLayout | None = None
    ignore_whitespace: bool | None = None
    sound_on_replies: bool | None = None


class GuideChange(WireModel):
    """Request body for PUT /api/guide — what the reader has now been shown."""

    model_config = ConfigDict(extra="forbid")

    seen_release: str = Field(min_length=1, max_length=MAX_RELEASE_LENGTH)
