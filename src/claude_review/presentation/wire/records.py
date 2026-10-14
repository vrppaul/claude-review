"""What every review on the machine keeps about its reader, as the page reads and changes it."""

from typing import override

from pydantic import ConfigDict, Field

from claude_review.domain import models
from claude_review.domain.interfaces import RecordChange
from claude_review.domain.models import DiffLayout, Theme
from claude_review.presentation.wire.base import WireBool, WireModel

# A release number, generously: 1.5.0, 1.5.0rc1, 1.4.3.dev0
MAX_RELEASE_LENGTH = 50


class ReaderSettings(WireModel):
    """How this reader reads a review, the same in every review on the machine."""

    theme: Theme
    diff_layout: DiffLayout
    # Leave out changes that only alter whitespace
    ignore_whitespace: WireBool
    # A tick when an answer arrives while the review is in a background tab
    sound_on_replies: WireBool
    # Ask the agent for a story of every change reviewed
    stories: WireBool


class GuideState(WireModel):
    """What the review remembers of having shown this reader around."""

    # The release whose news the reader was last shown
    seen_release: str | None
    # Whether Story has been introduced to the reader: by its release news, at the switch, or by their trying it
    story_introduced: WireBool


class KeptRecord[Record: WireModel](WireModel):
    """One record kept about the reader, and whether anything has been kept at all.

    A reader nothing has been kept about gets the defaults, and is told so:
    a page still holding choices made before they moved to the server hands
    them over once, when nothing is stored.
    """

    record: Record
    stored: WireBool


class SettingsChange(WireModel, RecordChange[models.ReaderSettings]):
    """Request body for PUT /api/settings — the choices being changed, and only those.

    A choice sent as null is a choice not sent, as in every change to what
    is kept about the reader.
    """

    model_config = ConfigDict(extra="forbid")

    theme: Theme | None = None
    diff_layout: DiffLayout | None = None
    ignore_whitespace: WireBool | None = None
    sound_on_replies: WireBool | None = None
    stories: WireBool | None = None

    @override
    def applied_to(self, record: models.ReaderSettings) -> models.ReaderSettings:
        """The reader's settings with each choice sent in place of theirs, and every other as it was kept."""
        return models.ReaderSettings(
            theme=_sent_or_kept(self.theme, record.theme),
            diff_layout=_sent_or_kept(self.diff_layout, record.diff_layout),
            ignore_whitespace=_sent_or_kept(self.ignore_whitespace, record.ignore_whitespace),
            sound_on_replies=_sent_or_kept(self.sound_on_replies, record.sound_on_replies),
            stories=_sent_or_kept(self.stories, record.stories),
        )


class GuideChange(WireModel, RecordChange[models.GuideState]):
    """Request body for PUT /api/guide — what the reader has now been shown, and only that.

    A fact sent as null is a fact not sent, as in every change to what is
    kept about the reader.
    """

    model_config = ConfigDict(extra="forbid")

    seen_release: str | None = Field(default=None, min_length=1, max_length=MAX_RELEASE_LENGTH)
    story_introduced: WireBool | None = None

    @override
    def applied_to(self, record: models.GuideState) -> models.GuideState:
        """What the review remembers of showing the reader around, with each fact sent in place of the one kept."""
        return models.GuideState(
            seen_release=_sent_or_kept(self.seen_release, record.seen_release),
            story_introduced=_sent_or_kept(self.story_introduced, record.story_introduced),
        )


def _sent_or_kept[Choice](sent: Choice | None, kept: Choice) -> Choice:
    """A choice as it was sent, or as it was kept when none was: null is a choice not sent."""
    return kept if sent is None else sent
