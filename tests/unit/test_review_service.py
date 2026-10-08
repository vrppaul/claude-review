"""Functional requirement tests for the review service.

These test the formatting of comments into markdown for Claude.
"""

from pathlib import Path

from claude_review.domain.models import CommentSeverity, LineSide, Turn, TurnAuthor
from claude_review.services.anchor_service import AnchorService
from claude_review.services.review_service import ReviewService
from tests.helpers import comment, line_anchor


def _service() -> ReviewService:
    return ReviewService(AnchorService([]))


def test_a_comment_is_filed_under_its_file_and_line() -> None:
    result = _service().format_review([comment(line_anchor("src/handler.ts", 42), "Wrong null check")])

    assert "### `src/handler.ts`:42" in result.markdown
    assert "Wrong null check" in result.markdown
    assert result.comment_count == 1


def test_a_comment_on_several_lines_is_filed_under_the_range() -> None:
    result = _service().format_review([comment(line_anchor("src/utils.py", 10, 15), "Refactor this block")])

    assert "### `src/utils.py`:10-15" in result.markdown
    assert "Refactor this block" in result.markdown


def test_comments_across_files_keep_the_order_they_were_written_in() -> None:
    comments = [
        comment(line_anchor("src/a.py", 1), "Fix A"),
        comment(line_anchor("src/b.py", 5), "Fix B"),
        comment(line_anchor("src/a.py", 20, 25), "Fix A again"),
    ]

    result = _service().format_review(comments)

    assert result.comment_count == 3
    first = result.markdown.index("### `src/a.py`:1\nFix A")
    second = result.markdown.index("### `src/b.py`:5\nFix B")
    third = result.markdown.index("### `src/a.py`:20-25\nFix A again")
    assert first < second < third


def test_a_review_with_nothing_in_it_says_nothing() -> None:
    result = _service().format_review([])

    assert result.comment_count == 0
    assert result.markdown == ""


def test_a_review_opens_with_its_heading() -> None:
    """The agent knows what it is reading before it reads any of it."""
    result = _service().format_review([comment(line_anchor("x.py", 1), "note")])

    assert result.markdown.startswith("## Code Review Comments")


def test_a_summary_alone_is_a_review() -> None:
    result = _service().format_review([], body="Wrong approach, let's use a different pattern.")

    assert result.comment_count == 1
    assert "Wrong approach" in result.markdown
    assert result.markdown.startswith("## Code Review Comments")


def test_the_summary_comes_before_the_comments() -> None:
    result = _service().format_review([comment(line_anchor("x.py", 1), "Fix this line")], body="Generally good.")

    assert result.comment_count == 2
    assert result.markdown.index("Generally good") < result.markdown.index("### `x.py`:1")


def test_a_summary_of_nothing_but_whitespace_is_no_summary() -> None:
    comments = [comment(line_anchor("x.py", 1), "note")]

    assert _service().format_review(comments, body="").comment_count == 1
    assert _service().format_review(comments, body="   \n  ").comment_count == 1


def test_no_summary_and_no_comments_says_nothing() -> None:
    result = _service().format_review([], body=None)

    assert result.comment_count == 0
    assert result.markdown == ""


def test_comment_on_a_removed_line_says_so() -> None:
    """A comment on the old side is marked, so its number is not read as current."""
    result = _service().format_review([comment(line_anchor("src/a.py", 42, side=LineSide.OLD), "Why drop this?")])

    assert "### `src/a.py`:42 (removed)" in result.markdown


def test_removed_range_is_marked_once() -> None:
    """A range on the old side keeps the range and the marker."""
    result = _service().format_review([comment(line_anchor("src/a.py", 10, 14, side=LineSide.OLD), "Restore this")])

    assert "### `src/a.py`:10-14 (removed)" in result.markdown


def test_same_line_number_on_both_sides_stays_distinguishable() -> None:
    """A replaced line has an old 42 and a new 42; the output tells them apart."""
    comments = [
        comment(line_anchor("src/a.py", 42, side=LineSide.OLD), "The old one"),
        comment(line_anchor("src/a.py", 42), "The new one"),
    ]

    result = _service().format_review(comments)

    assert "### `src/a.py`:42 (removed)\nThe old one" in result.markdown
    assert "### `src/a.py`:42\nThe new one" in result.markdown
    assert result.comment_count == 2


def test_a_question_is_marked_as_one() -> None:
    """A question wants an answer before anything changes."""
    asked = comment(line_anchor("src/a.py", 4), "Is this reachable?", severity=CommentSeverity.QUESTION)

    assert "### `src/a.py`:4 — question" in _service().format_review([asked]).markdown


def test_a_blocker_is_marked_as_one() -> None:
    blocking = comment(line_anchor("src/a.py", 4), "This drops the lock", severity=CommentSeverity.BLOCKER)

    assert "### `src/a.py`:4 — blocker" in _service().format_review([blocking]).markdown


def test_an_ordinary_note_is_left_unmarked() -> None:
    """Most comments are notes, so saying so on each would be noise."""
    markdown = _service().format_review([comment(line_anchor("src/a.py", 4), "Reads well")]).markdown

    assert "### `src/a.py`:4\n" in markdown
    assert "note" not in markdown


def test_an_answered_thread_carries_the_conversation() -> None:
    """A thread that was discussed sends its turns, not only its first line."""
    discussed = comment(
        line_anchor("src/state.py", 60, 64),
        "Every open review gets this push. Deliberate?",
        severity=CommentSeverity.QUESTION,
        turns=[
            Turn(author=TurnAuthor.AUTHOR, body="Deliberate: two tabs are one reader."),
            Turn(author=TurnAuthor.READER, body="Then say so in the docstring."),
        ],
    )

    markdown = _service().format_review([discussed]).markdown

    assert "Every open review gets this push. Deliberate?" in markdown
    assert "> **You:** Deliberate: two tabs are one reader." in markdown
    assert "> **Reviewer:** Then say so in the docstring." in markdown


def test_a_settled_thread_says_it_is_settled() -> None:
    """Resolved is on the comment, so it survives into what the agent reads."""
    settled = comment(line_anchor("src/state.py", 60), "Deliberate?", severity=CommentSeverity.QUESTION, resolved=True)

    assert "### `src/state.py`:60 — question, resolved" in _service().format_review([settled]).markdown


def test_a_comment_whose_lines_moved_carries_what_it_was_written_against() -> None:
    """An outdated anchor is useless alone, so the lines travel with it."""
    written_against = ["asked = ensure_future(state.questions.get())", "closed = ensure_future(state.wait())"]
    moved = line_anchor("src/routes.py", 104, 105, quote=written_against, outdated=True)

    markdown = _service().format_review([comment(moved, "Two mechanisms for one review.")]).markdown

    assert "outdated" in markdown
    assert "asked = ensure_future(state.questions.get())" in markdown
    assert "Two mechanisms for one review." in markdown


def test_a_later_round_says_which_round_it_is() -> None:
    """A round is a reply to the work done since the last one."""
    result = _service().format_review([comment(line_anchor("src/a.py", 1), "Still reads oddly.")], round_number=2)

    assert result.markdown.startswith("## Code Review Comments — round 2")


def test_the_first_round_is_not_numbered() -> None:
    """One round is just a review; numbering it would only add noise."""
    result = _service().format_review([comment(line_anchor("src/a.py", 1), "Fine.")], round_number=1)

    assert result.markdown.startswith("## Code Review Comments\n")


def test_a_thread_the_author_raised_reads_as_the_authors_own_words() -> None:
    """Otherwise the agent is handed its own note back as an instruction."""
    raised = comment(
        line_anchor("src/a.py", 42),
        "I renamed this rather than deleting it",
        raised_by=TurnAuthor.AUTHOR,
        turns=[Turn(author=TurnAuthor.READER, body="Good, but call it `head`")],
    )

    markdown = _service().format_review([raised]).markdown

    assert "> **You:** I renamed this rather than deleting it" in markdown
    assert "> **Reviewer:** Good, but call it `head`" in markdown


def test_images_are_named_as_files_to_open() -> None:
    """The agent reads files, so a screenshot in a thread is a path under what it came with."""
    opening = Path("/review/images/opening.png")
    reply = Path("/review/images/reply.png")
    pictured = comment(
        line_anchor("src/handler.ts", 42),
        "",
        images=[opening],
        turns=[Turn(author=TurnAuthor.READER, body="Still like this", images=[reply])],
    )

    markdown = _service().format_review([pictured]).markdown

    assert f"Image: {opening}" in markdown
    assert f"> **Reviewer:**\n> Still like this\n> Image: {reply}" in markdown


def test_a_comment_reaches_the_agent_as_written() -> None:
    """Line endings and a trailing newline are the reader's, not the formatter's."""
    body = "first\r\nsecond\n"

    assert body in _service().format_review([comment(line_anchor("src/handler.ts", 1), body)]).markdown
