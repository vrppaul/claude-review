"""Functional requirement tests for a thread on the story's words: it quotes what the story says there, and follows them.

A block of the story is known by a place: the overview's lines by name, a
chapter by its id, a step by its file and first line, an item by where it
stands in its list. A thread there is about the words it quotes. Told
again, the story may say them at another block, and the thread moves there;
where it says them nowhere, the thread stays where it hangs, outdated.
"""

import pytest
from pydantic import ValidationError

from claude_review.domain.exceptions import FieldPath, UnknownStoryBlockError
from claude_review.domain.models import (
    NO_HUNK_HEADER,
    ChapterBlock,
    ChapterText,
    DiffHunk,
    ItemBlock,
    LineSpan,
    OverviewBlock,
    OverviewList,
    OverviewText,
    ReasonBlock,
    StoryAnchor,
    StoryBlock,
)
from claude_review.domain.story import Step
from claude_review.services.anchor_service import StoryAnchorHandler
from claude_review.services.story_telling import follow, tell
from tests.helpers import added_line, removed_line
from tests.stories import (
    IMAGE_SERVICE,
    KEEPING_CHAPTER,
    PASTE_CHAPTER,
    canvas_story,
    changed_file,
    field_at,
    planted,
    story_of,
    told_as_written,
)

STORY = canvas_story()
HELD = StoryAnchorHandler(told_as_written(STORY))
NO_STORY = StoryAnchorHandler(None)

# A file whose first line a change rewrote, a step that says why, and the line said another way again since:
# nothing of the step's code is found, and it shows none
REWRITTEN = "src/rewritten.py"
FIRST_LINE = LineSpan(first=1, last=1)
WHY_REWRITTEN = "Said as the caller expects."
REWRITTEN_ONCE = [
    changed_file(
        REWRITTEN,
        DiffHunk(header=NO_HUNK_HEADER, old_start=1, new_start=1, lines=[removed_line(1, "a"), added_line(1, "A")]),
    )
]
REWRITTEN_AGAIN = [
    changed_file(
        REWRITTEN,
        DiffHunk(header=NO_HUNK_HEADER, old_start=1, new_start=1, lines=[removed_line(1, "a"), added_line(1, "Aa")]),
    )
]

# The rewritten first line pushed two lines down by two put above it, said as it was
PUSHED_DOWN = [
    changed_file(
        REWRITTEN,
        DiffHunk(
            header=NO_HUNK_HEADER,
            old_start=1,
            new_start=1,
            lines=[added_line(1, "x"), added_line(2, "y"), removed_line(1, "a"), added_line(3, "A")],
        ),
    )
]

THE_DOUBT = OverviewBlock(text=OverviewText.DOUBT)
THE_DOUBT_SAID = ("overview", "doubt")
# Words the story never said, as a thread on a block may quote them
OTHER_WORDS = "Whether anything is checked at all."

# Every kind of block, and where the story's document holds its words
BLOCKS_AND_THEIR_WORDS: list[tuple[StoryBlock, FieldPath]] = [
    (OverviewBlock(text=OverviewText.TASK), ("overview", "task")),
    (ItemBlock(list=OverviewList.DECISIONS, item=1), ("overview", "decisions", 1, "text")),
    (ChapterBlock(chapter=KEEPING_CHAPTER, text=ChapterText.DOUBT), ("chapters", 1, "doubt")),
    (ReasonBlock(file=IMAGE_SERVICE, first_line=102), ("chapters", 1, "steps", 1, "reason")),
]
# Blocks the story does not say: a chapter with no doubt, a chapter it has not, an item past the end of its
# list, and lines no step of a file starts at
BLOCKS_NOT_SAID: list[StoryBlock] = [
    ChapterBlock(chapter=PASTE_CHAPTER, text=ChapterText.DOUBT),
    ChapterBlock(chapter="ch-9", text=ChapterText.WHY),
    ItemBlock(list=OverviewList.LATER, item=2),
    ReasonBlock(file=IMAGE_SERVICE, first_line=103),
]


@pytest.mark.parametrize(("block", "said_at"), BLOCKS_AND_THEIR_WORDS)
def test_a_thread_on_a_block_quotes_the_words_the_story_says_there(block: StoryBlock, said_at: FieldPath) -> None:
    quoted = HELD.quote(StoryAnchor(block=block))

    assert quoted == StoryAnchor(block=block, quote=[field_at(STORY, said_at)])


@pytest.mark.parametrize("block", BLOCKS_NOT_SAID)
def test_a_thread_on_words_the_story_does_not_say_is_refused(block: StoryBlock) -> None:
    with pytest.raises(UnknownStoryBlockError):
        HELD.quote(StoryAnchor(block=block))


def test_a_story_that_tells_a_file_no_thread_could_name_still_takes_threads_on_its_other_words() -> None:
    """Git hands out such names, and a story tells the file; only a thread on that step's reason has no place."""
    named_oddly = planted(STORY, ("chapters", 0, "steps", 0, "file"), "images\tts")
    held = StoryAnchorHandler(told_as_written(named_oddly))

    assert held.quote(StoryAnchor(block=THE_DOUBT)).quote == [field_at(STORY, THE_DOUBT_SAID)]


def test_the_reason_of_a_step_whose_code_a_round_took_out_of_sight_may_still_be_asked_about() -> None:
    """Its words are still drawn though it shows no code: a thread on them has its place."""
    told = tell(story_of(Step(file=REWRITTEN, lines=FIRST_LINE, reason=WHY_REWRITTEN)), REWRITTEN_ONCE)
    held = StoryAnchorHandler(follow(told, REWRITTEN_AGAIN))

    assert held.quote(StoryAnchor(block=ReasonBlock(file=REWRITTEN, first_line=FIRST_LINE.first))).quote == [
        WHY_REWRITTEN
    ]


def test_a_thread_on_a_steps_reason_keeps_its_block_once_a_round_moves_the_steps_code() -> None:
    """A step is known by where it was told: its code two lines down, its reason is still where the thread hangs."""
    told = tell(story_of(Step(file=REWRITTEN, lines=FIRST_LINE, reason=WHY_REWRITTEN)), REWRITTEN_ONCE)
    held = StoryAnchorHandler(follow(told, PUSHED_DOWN))
    on_the_reason = StoryAnchor(block=ReasonBlock(file=REWRITTEN, first_line=FIRST_LINE.first), quote=[WHY_REWRITTEN])

    assert held.follow(on_the_reason) == on_the_reason


def test_a_thread_on_the_story_is_refused_while_no_story_is_told() -> None:
    with pytest.raises(UnknownStoryBlockError):
        NO_STORY.quote(StoryAnchor(block=THE_DOUBT))


def test_a_thread_whose_block_still_says_its_words_stays_on_it() -> None:
    """Even one marked outdated by a story told between: told once more, the words are back."""
    said = StoryAnchor(block=THE_DOUBT, quote=[field_at(STORY, THE_DOUBT_SAID)], outdated=True)

    assert HELD.follow(said) == StoryAnchor(block=THE_DOUBT, quote=said.quote)


def test_a_thread_on_words_the_story_says_nowhere_now_is_outdated_where_it_hangs() -> None:
    written = StoryAnchor(block=THE_DOUBT, quote=[OTHER_WORDS])

    assert HELD.follow(written) == StoryAnchor(block=THE_DOUBT, quote=[OTHER_WORDS], outdated=True)


def test_a_thread_on_a_chapter_the_story_no_longer_tells_is_outdated_where_it_hangs() -> None:
    gone = ChapterBlock(chapter="ch-9", text=ChapterText.WHY)

    assert HELD.follow(StoryAnchor(block=gone, quote=[OTHER_WORDS])) == StoryAnchor(
        block=gone, quote=[OTHER_WORDS], outdated=True
    )


def test_a_thread_follows_its_item_moved_down_the_list() -> None:
    words = field_at(STORY, ("overview", "decisions", 0, "text"))
    second_words = field_at(STORY, ("overview", "decisions", 1, "text"))
    swapped = planted(
        planted(STORY, ("overview", "decisions", 0, "text"), second_words), ("overview", "decisions", 1, "text"), words
    )
    written = StoryAnchor(block=ItemBlock(list=OverviewList.DECISIONS, item=0), quote=[words])

    followed = StoryAnchorHandler(told_as_written(swapped)).follow(written)

    assert followed == StoryAnchor(block=ItemBlock(list=OverviewList.DECISIONS, item=1), quote=[words])


def test_a_thread_follows_its_words_to_another_block_and_another_chapter() -> None:
    """A story told again may say a doubt of the overview as a chapter's: the thread is about the words."""
    doubt = field_at(STORY, THE_DOUBT_SAID)
    moved = planted(planted(STORY, THE_DOUBT_SAID, None), ("chapters", 0, "doubt"), doubt)

    followed = StoryAnchorHandler(told_as_written(moved)).follow(StoryAnchor(block=THE_DOUBT, quote=[doubt]))

    assert followed == StoryAnchor(block=ChapterBlock(chapter=PASTE_CHAPTER, text=ChapterText.DOUBT), quote=[doubt])


def test_a_thread_whose_words_its_block_and_another_both_say_stays_on_its_own() -> None:
    doubt = field_at(STORY, THE_DOUBT_SAID)
    said_twice = planted(STORY, ("chapters", 0, "doubt"), doubt)

    followed = StoryAnchorHandler(told_as_written(said_twice)).follow(StoryAnchor(block=THE_DOUBT, quote=[doubt]))

    assert followed == StoryAnchor(block=THE_DOUBT, quote=[doubt])


def test_a_thread_whose_words_two_other_blocks_say_moves_to_the_first_the_story_tells() -> None:
    task = field_at(STORY, ("overview", "task"))
    said_twice = planted(planted(STORY, ("chapters", 1, "why"), task), ("chapters", 0, "why"), task)
    elsewhere = StoryAnchor(block=ChapterBlock(chapter="ch-9", text=ChapterText.WHY), quote=[task])

    followed = StoryAnchorHandler(told_as_written(said_twice)).follow(elsewhere)

    assert followed == StoryAnchor(block=OverviewBlock(text=OverviewText.TASK), quote=[task])


def test_a_thread_on_the_story_is_left_as_it_is_while_no_story_is_held() -> None:
    """A review restarted holds no story until one is told again: nothing says the words changed."""
    written = StoryAnchor(block=THE_DOUBT, quote=[OTHER_WORDS], outdated=True)

    assert NO_STORY.follow(written) == written


def test_a_thread_on_the_story_is_taken_with_the_words_the_page_showed() -> None:
    """No suggestion replaces a story's words, so nothing holds the quote to them: the page quotes what it drew."""
    HELD.check_quote(StoryAnchor(block=THE_DOUBT, quote=[OTHER_WORDS]))


def test_what_a_thread_on_the_story_is_on_is_the_words_it_quotes() -> None:
    assert HELD.excerpt(StoryAnchor(block=THE_DOUBT, quote=[OTHER_WORDS])) == [OTHER_WORDS]


def test_a_step_is_known_by_a_line_a_file_could_have() -> None:
    with pytest.raises(ValidationError):
        ReasonBlock(file=IMAGE_SERVICE, first_line=0)


def test_a_thread_on_the_story_quotes_its_block_as_one_text() -> None:
    with pytest.raises(ValidationError):
        StoryAnchor(block=THE_DOUBT, quote=[OTHER_WORDS, OTHER_WORDS])
