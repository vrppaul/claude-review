"""How the page names a review's bases: the keys it asks by, and the words it shows."""

import pytest
from hypothesis import given, strategies as strategy

from claude_review.domain.exceptions import UnknownVersionError
from claude_review.domain.models import FIRST_ROUND, HEAD, ChangedSinceRound, RefKey, ReviewKey, RoundKey, VersionKey
from claude_review.presentation.version_labels import (
    REF_PREFIX,
    REVIEW_KEY,
    ROUND_PREFIX,
    changes_since_round,
    key_of,
    key_text,
    label_of,
    phrase_of,
)

# What a review is opened against when it is opened against a ref
OPENED_AGAINST = "v1.4.0"

# Every key a review can hand out: its own, any round's, any ref's
keys = strategy.one_of(
    strategy.just(ReviewKey()),
    strategy.builds(RoundKey, round=strategy.integers(min_value=FIRST_ROUND)),
    strategy.builds(RefKey, name=strategy.text(min_size=1)),
)
# Anything a page might send: a kind of key it knows, or none, followed by
# anything at all — digits above all, in any script, which a round's key ends in
tails = strategy.one_of(strategy.text(), strategy.from_regex(r"\d+", fullmatch=True))
sent_keys = strategy.tuples(strategy.sampled_from([REVIEW_KEY, ROUND_PREFIX, REF_PREFIX, ""]), tails).map("".join)


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
    ["round:0", "round:abc", "round:", "round:02", "round:\U0001d7cf", "ref:", "branch:main", ""],
    ids=[
        "round-zero",
        "round-not-a-number",
        "round-empty",
        "round-leading-zero",
        "round-digit-of-another-script",
        "ref-empty",
        "no-kind",
        "nothing",
    ],
)
def test_a_key_this_review_never_hands_out_is_refused(text: str) -> None:
    with pytest.raises(UnknownVersionError):
        key_of(text)


@given(key=keys)
def test_every_key_the_page_is_handed_names_the_base_it_came_from(key: VersionKey) -> None:
    assert key_of(key_text(key)) == key


@given(text=sent_keys)
def test_a_key_is_taken_only_as_the_review_writes_it(text: str) -> None:
    """No second spelling of one base: what is taken is written back the same way, and the rest refused."""
    try:
        key = key_of(text)
    except UnknownVersionError:
        return
    assert key_text(key) == text


def test_a_round_is_named_the_way_the_header_will_say_it() -> None:
    assert phrase_of(RoundKey(round=2), OPENED_AGAINST) == "changes since round 2"
    assert label_of(RoundKey(round=2), OPENED_AGAINST) == "round 2"


def test_the_review_is_named_by_what_it_was_opened_against() -> None:
    """ "Uncommitted changes" is not "changes since" anything."""
    assert phrase_of(ReviewKey(), OPENED_AGAINST) == f"changes since {OPENED_AGAINST}"
    assert phrase_of(ReviewKey(), None) == "uncommitted changes"
    assert phrase_of(RefKey(name=HEAD), OPENED_AGAINST) == "uncommitted changes"


def test_what_changed_since_a_round_carries_the_key_that_shows_just_that() -> None:
    told = changes_since_round(ChangedSinceRound(round=3, paths=["a.py"]))

    assert told is not None
    assert (told.since_round, told.base_key, told.paths) == (3, "round:3", ["a.py"])
