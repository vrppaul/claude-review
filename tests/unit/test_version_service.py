"""Which bases a review offers, out of the marks it has left.

The right-hand side of the diff is always the working tree, so a base is the
only thing there is to choose — and the only ones worth offering are the ones
that would show something.
"""

from claude_review.domain.models import TreeSnapshot, VersionKind
from claude_review.repositories.git_repository import GitRepository
from claude_review.services.version_service import VersionService


def _service() -> VersionService:
    """Sorting the marks a review has left asks git nothing."""
    return VersionService(git_repository=GitRepository())


def test_every_round_that_has_a_mark_is_on_offer() -> None:
    rounds = _service().rounds(
        [
            TreeSnapshot(round=1, tree="aaa", at=1),
            TreeSnapshot(round=2, tree="bbb", at=2),
            TreeSnapshot(round=3, tree="ccc", at=3),
        ]
    )

    assert [r.key for r in rounds] == ["round:1", "round:2", "round:3"]
    assert [r.label for r in rounds] == ["round 1", "round 2", "round 3"]
    assert {r.kind for r in rounds} == {VersionKind.ROUND}


def test_a_round_is_named_the_way_the_header_will_say_it() -> None:
    listed = _service().rounds([TreeSnapshot(round=2, tree="aaa", at=1)])

    assert listed[0].phrase == "changes since round 2"


def test_a_round_is_remembered_as_it_began() -> None:
    """The agent may retake the diff twice in one round; the round started once."""
    rounds = _service().rounds(
        [
            TreeSnapshot(round=1, tree="aaa", at=1),
            TreeSnapshot(round=2, tree="bbb", at=2),
            TreeSnapshot(round=2, tree="ccc", at=3),
        ]
    )

    assert [(r.key, r.at) for r in rounds] == [("round:1", 1), ("round:2", 2)]


def test_a_review_that_has_left_no_marks_offers_no_rounds() -> None:
    assert _service().rounds([]) == []
