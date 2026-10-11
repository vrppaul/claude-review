"""How the page names the bases a review offers: the key it asks for one by, and the words it shows for it.

The review keeps its bases typed; the page asks for one by a short key it
never has to build itself, and is told what to call it. "Uncommitted
changes" is not "changes since" anything, which is why the words are
written on this side rather than assembled in the page — in the same words
the review's title says what it is compared against.
"""

import re
from typing import assert_never

from claude_review.domain.exceptions import UnknownVersionError
from claude_review.domain.models import (
    HEAD,
    ChangedSinceRound,
    RefKey,
    ReviewKey,
    RoundKey,
    VersionKey,
    VersionOnOffer,
)
from claude_review.presentation.wire.content import ChangesSince, ReviewVersion, VersionKind
from claude_review.services.review_opening import UNCOMMITTED, changes_since

# The keys, as the page holds them: the review's own base, and the prefixes
# a round's and a ref's are written with
REVIEW_KEY = "review"
ROUND_PREFIX = "round:"
REF_PREFIX = "ref:"
# A round's number as the review writes it: plain digits, no leading zero —
# the one spelling, so a key names one base and a base has one key
ROUND_NUMBER = re.compile(r"[1-9][0-9]*")
# What a round is called as a base
ROUND_LABEL = "round {number}"


def key_text(key: VersionKey) -> str:
    """The key a page asks for a base by."""
    match key:
        case ReviewKey():
            return REVIEW_KEY
        case RoundKey():
            return f"{ROUND_PREFIX}{key.round}"
        case RefKey():
            return f"{REF_PREFIX}{key.name}"
        case _:
            assert_never(key)


def key_of(text: str) -> VersionKey:
    """The base a page's key names.

    Raises:
        UnknownVersionError: if it is not a key this review hands out.
    """
    if text == REVIEW_KEY:
        return ReviewKey()
    number = text.removeprefix(ROUND_PREFIX)
    if text.startswith(ROUND_PREFIX) and ROUND_NUMBER.fullmatch(number):
        return RoundKey(round=int(number))
    name = text.removeprefix(REF_PREFIX)
    if text.startswith(REF_PREFIX) and name:
        return RefKey(name=name)
    msg = f"nothing here is compared against {text}"
    raise UnknownVersionError(msg)


def phrase_of(key: VersionKey, opened_against: str | None) -> str:
    """What the header says while this base is the one in force."""
    match key:
        case ReviewKey():
            return changes_since(opened_against)
        case RoundKey():
            return changes_since(ROUND_LABEL.format(number=key.round))
        case RefKey():
            # What differs from HEAD is what is not committed yet
            return changes_since(None if key.name == HEAD else key.name)
        case _:
            assert_never(key)


def label_of(key: VersionKey, opened_against: str | None) -> str:
    """What a row of the menu calls this base."""
    match key:
        case ReviewKey():
            return opened_against or UNCOMMITTED
        case RoundKey():
            return ROUND_LABEL.format(number=key.round)
        case RefKey():
            return key.name
        case _:
            assert_never(key)


def kind_of(key: VersionKey) -> VersionKind:
    match key:
        case ReviewKey():
            return VersionKind.REVIEW
        case RoundKey():
            return VersionKind.ROUND
        case RefKey():
            return VersionKind.REF
        case _:
            assert_never(key)


def version_on_the_wire(offered: VersionOnOffer, opened_against: str | None) -> ReviewVersion:
    """A base on offer, as the page's menu shows it."""
    return ReviewVersion(
        key=key_text(offered.key),
        kind=kind_of(offered.key),
        label=label_of(offered.key, opened_against),
        phrase=phrase_of(offered.key, opened_against),
        at=offered.at,
        changed=offered.changed,
    )


def changes_on_the_wire(changes: ChangedSinceRound | None) -> ChangesSince | None:
    """What changed since a round began, with the key that shows just that."""
    if changes is None:
        return None
    return ChangesSince(
        since_round=changes.round, base_key=key_text(RoundKey(round=changes.round)), paths=changes.paths
    )
