"""How the page names a review's bases: the keys it asks by, and the words it shows."""

import pytest

from claude_review.domain.exceptions import UnknownVersionError
from claude_review.domain.models import HEAD, ChangedSinceRound, RefKey, ReviewKey, RoundKey, VersionKey
from claude_review.presentation.version_words import changes_on_the_wire, key_of, key_text, label_of, phrase_of

# What a review is opened against when it is opened against a ref
OPENED_AGAINST = "v1.4.0"


@pytest.mark.parametrize(
    ("key", "text"),
    [(ReviewKey(), "review"), (RoundKey(round=2), "round:2"), (RefKey(name="main"), "ref:main")],
    ids=["review", "round", "ref"],
)
def test_a_key_the_page_holds_names_the_base_it_came_from(key: VersionKey, text: str) -> None:
    assert key_text(key) == text
    assert key_of(text) == key


@pytest.mark.parametrize(
    "text",
    ["round:0", "round:abc", "round:", "ref:", "branch:main", ""],
    ids=["round-zero", "round-not-a-number", "round-empty", "ref-empty", "no-kind", "nothing"],
)
def test_a_key_this_review_never_hands_out_is_refused(text: str) -> None:
    with pytest.raises(UnknownVersionError):
        key_of(text)


def test_a_round_is_named_the_way_the_header_will_say_it() -> None:
    assert phrase_of(RoundKey(round=2), OPENED_AGAINST) == "changes since round 2"
    assert label_of(RoundKey(round=2), OPENED_AGAINST) == "round 2"


def test_the_review_is_named_by_what_it_was_opened_against() -> None:
    """ "Uncommitted changes" is not "changes since" anything."""
    assert phrase_of(ReviewKey(), OPENED_AGAINST) == f"changes since {OPENED_AGAINST}"
    assert phrase_of(ReviewKey(), None) == "uncommitted changes"
    assert phrase_of(RefKey(name=HEAD), OPENED_AGAINST) == "uncommitted changes"


def test_what_changed_since_a_round_carries_the_key_that_shows_just_that() -> None:
    told = changes_on_the_wire(ChangedSinceRound(round=3, paths=["a.py"]))

    assert told is not None
    assert (told.since_round, told.base_key, told.paths) == (3, "round:3", ["a.py"])
