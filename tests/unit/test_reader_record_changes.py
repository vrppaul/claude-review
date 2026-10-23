"""Functional requirement tests for a change to what is kept about a reader: each choice takes its own place.

The page sends the choices being changed, and only those. A choice sent
takes the place of the one kept; one not sent, or sent as null, leaves it;
and no choice lands where another belongs, though two of them are each a
yes or a no.
"""

import pytest
from pydantic import BaseModel, ConfigDict

from claude_review.domain.models import DiffLayout, GuideState, ReaderSettings, StoryWriting, Theme
from claude_review.presentation.schemas.records import GuideChange, SettingsChange

# How a reader reads, with the choices that are a yes or a no not all kept alike
KEPT = ReaderSettings(
    theme=Theme.DARK,
    diff_layout=DiffLayout.SPLIT,
    ignore_whitespace=True,
    sound_on_replies=False,
    story_writing=StoryWriting.WITHOUT_ASKING,
)


class Choice(BaseModel):
    """One choice a reader changes, and how they read once it is changed."""

    model_config = ConfigDict(frozen=True)

    what: str
    change: SettingsChange
    leaves: ReaderSettings


CHOICES = [
    Choice(
        what="the theme",
        change=SettingsChange(theme=Theme.LIGHT),
        leaves=ReaderSettings(
            theme=Theme.LIGHT,
            diff_layout=DiffLayout.SPLIT,
            ignore_whitespace=True,
            sound_on_replies=False,
            story_writing=StoryWriting.WITHOUT_ASKING,
        ),
    ),
    Choice(
        what="how a diff is laid out",
        change=SettingsChange(diff_layout=DiffLayout.UNIFIED),
        leaves=ReaderSettings(
            theme=Theme.DARK,
            diff_layout=DiffLayout.UNIFIED,
            ignore_whitespace=True,
            sound_on_replies=False,
            story_writing=StoryWriting.WITHOUT_ASKING,
        ),
    ),
    Choice(
        what="whether whitespace is left out",
        change=SettingsChange(ignore_whitespace=False),
        leaves=ReaderSettings(
            theme=Theme.DARK,
            diff_layout=DiffLayout.SPLIT,
            ignore_whitespace=False,
            sound_on_replies=False,
            story_writing=StoryWriting.WITHOUT_ASKING,
        ),
    ),
    Choice(
        what="whether a reply sounds",
        change=SettingsChange(sound_on_replies=True),
        leaves=ReaderSettings(
            theme=Theme.DARK,
            diff_layout=DiffLayout.SPLIT,
            ignore_whitespace=True,
            sound_on_replies=True,
            story_writing=StoryWriting.WITHOUT_ASKING,
        ),
    ),
    Choice(
        what="when a story is written",
        change=SettingsChange(story_writing=StoryWriting.AS_THE_REVIEW_OPENS),
        leaves=ReaderSettings(
            theme=Theme.DARK,
            diff_layout=DiffLayout.SPLIT,
            ignore_whitespace=True,
            sound_on_replies=False,
            story_writing=StoryWriting.AS_THE_REVIEW_OPENS,
        ),
    ),
]


@pytest.mark.parametrize("choice", CHOICES, ids=[choice.what for choice in CHOICES])
def test_a_choice_sent_takes_the_place_of_the_one_kept_and_leaves_every_other(choice: Choice) -> None:
    assert choice.change.applied_to(KEPT) == choice.leaves


def test_a_change_that_sends_no_choice_leaves_the_reader_as_they_were() -> None:
    assert SettingsChange().applied_to(KEPT) == KEPT


def test_a_reader_shown_a_later_release_is_remembered_as_shown_it_and_still_introduced_to_story() -> None:
    assert GuideChange(seen_release="1.6.0").applied_to(
        GuideState(seen_release="1.5.0", story_introduced=True)
    ) == GuideState(seen_release="1.6.0", story_introduced=True)


def test_a_reader_introduced_to_story_is_still_remembered_as_shown_their_release() -> None:
    assert GuideChange(story_introduced=True).applied_to(GuideState(seen_release="1.5.0")) == GuideState(
        seen_release="1.5.0", story_introduced=True
    )
