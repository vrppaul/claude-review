"""What every review on the machine keeps about its reader, as the page reads and changes it."""

from typing import Self, override

from pydantic import ConfigDict, Field, StrictBool

from claude_review.domain import models
from claude_review.domain.interfaces import RecordChange
from claude_review.domain.models import DiffLayout, StoryWriting, Theme
from claude_review.presentation.schemas.base import Schema

# A release number, generously: 1.5.0, 1.5.0rc1, 1.4.3.dev0
MAX_RELEASE_LENGTH = 50


class ReaderSettings(Schema):
    """How this reader reads a review, the same in every review on the machine."""

    theme: Theme
    diff_layout: DiffLayout
    # Leave out changes that only alter whitespace
    ignore_whitespace: StrictBool
    # A tick when an answer arrives while the review is in a background tab
    sound_on_replies: StrictBool
    # When a review's story is written: asked first, at once at a press on Story, or as each review opens
    story_writing: StoryWriting

    @classmethod
    def from_domain(cls, settings: models.ReaderSettings) -> Self:
        return cls(
            theme=settings.theme,
            diff_layout=settings.diff_layout,
            ignore_whitespace=settings.ignore_whitespace,
            sound_on_replies=settings.sound_on_replies,
            story_writing=settings.story_writing,
        )


class GuideState(Schema):
    """What the review remembers of having shown this reader around."""

    # The release whose news the reader was last shown
    seen_release: str | None
    # Whether Story has been introduced to the reader: by its release news, at the switch, or by their trying it
    story_introduced: StrictBool
    # Whether Send feedback has been introduced to the reader: under Help, or by their opening it
    feedback_introduced: StrictBool

    @classmethod
    def from_domain(cls, guide: models.GuideState) -> Self:
        return cls(
            seen_release=guide.seen_release,
            story_introduced=guide.story_introduced,
            feedback_introduced=guide.feedback_introduced,
        )


class KeptRecord[Record: Schema](Schema):
    """One record kept about the reader, and whether anything has been kept at all.

    A reader nothing has been kept about gets the defaults, and is told so:
    a page still holding choices made before they moved to the server hands
    them over once, when nothing is stored.
    """

    record: Record
    stored: StrictBool


class SettingsChange(Schema, RecordChange[models.ReaderSettings]):
    """Request body for PUT /api/settings — the choices being changed, and only those.

    A choice sent as null is a choice not sent, as in every change to what
    is kept about the reader.
    """

    model_config = ConfigDict(extra="forbid")

    theme: Theme | None = None
    diff_layout: DiffLayout | None = None
    ignore_whitespace: StrictBool | None = None
    sound_on_replies: StrictBool | None = None
    story_writing: StoryWriting | None = None

    @override
    def applied_to(self, record: models.ReaderSettings) -> models.ReaderSettings:
        """The reader's settings with each choice sent in place of theirs, and every other as it was kept."""
        return models.ReaderSettings(
            theme=_sent_or_kept(self.theme, record.theme),
            diff_layout=_sent_or_kept(self.diff_layout, record.diff_layout),
            ignore_whitespace=_sent_or_kept(self.ignore_whitespace, record.ignore_whitespace),
            sound_on_replies=_sent_or_kept(self.sound_on_replies, record.sound_on_replies),
            story_writing=_sent_or_kept(self.story_writing, record.story_writing),
        )


class GuideChange(Schema, RecordChange[models.GuideState]):
    """Request body for PUT /api/guide — what the reader has now been shown, and only that.

    A fact sent as null is a fact not sent, as in every change to what is
    kept about the reader.
    """

    model_config = ConfigDict(extra="forbid")

    seen_release: str | None = Field(default=None, min_length=1, max_length=MAX_RELEASE_LENGTH)
    story_introduced: StrictBool | None = None
    feedback_introduced: StrictBool | None = None

    @override
    def applied_to(self, record: models.GuideState) -> models.GuideState:
        """What the review remembers of showing the reader around, with each fact sent in place of the one kept."""
        return models.GuideState(
            seen_release=_sent_or_kept(self.seen_release, record.seen_release),
            story_introduced=_sent_or_kept(self.story_introduced, record.story_introduced),
            feedback_introduced=_sent_or_kept(self.feedback_introduced, record.feedback_introduced),
        )


def _sent_or_kept[Choice](sent: Choice | None, kept: Choice) -> Choice:
    """A choice as it was sent, or as it was kept when none was: null is a choice not sent."""
    return kept if sent is None else sent
