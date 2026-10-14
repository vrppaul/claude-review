"""The story a review holds: the last one the agent told of its change, on the take of it on screen.

A story is told of the change as it stood, and kept as it was told, with
the round it was told in, until the next telling replaces it whole. The
round's work then moves the code under it, and each take of the change the
review makes, the story told is followed onto: the story held is that one,
showing the code as it now stands and saying whether it moved on. It is
always followed from the story as it was told, whose pieces are what each
step was told with, as a thread follows from its quote. Its pieces are cut
out of one take of the change, so it says which: a page that read the diff
of a later take can tell that they are not yet of the code it shows.

The reader may ask for a story rather than wait to be told one. That
asking is kept here, beside the story that ends it: when it was asked, when
an agent took the request, whether the reader stopped it. A story is asked
for only while no story held is current — none is held, or a round moved
the code on under it — and none is awaited, so however many pages ask,
and however often, the review is asked once.
"""

import asyncio

from pydantic import BaseModel, ConfigDict, Field

from claude_review.domain.interfaces import Clock
from claude_review.domain.models import FIRST_ROUND, StaleStep, StoryWentStale
from claude_review.domain.story import FollowedStep, Step, Story, StoryAsking, ToldStep, ToldStory
from claude_review.services import story_telling
from claude_review.services.review.review_content import FIRST_TAKE, ReviewContent


class LeftOutChanged(BaseModel):
    """How many changed lines no step told when a story was told, and how many none tells now."""

    model_config = ConfigDict(frozen=True)

    when_told: int
    now: int


class CodeMovedOn(BaseModel):
    """That a round's work moved the code under a story told before it: in which round, and how much is left out."""

    model_config = ConfigDict(frozen=True)

    # The round of the take that first found it so: a later take that finds
    # it still so keeps it
    round: int = Field(ge=FIRST_ROUND)
    # Said only where the round changed how much is left out; None where as
    # much is left out as when it was told
    left_out: LeftOutChanged | None


class StoryHeld(BaseModel):
    """A story as the review holds it: on a take of the change, with the round it was told in."""

    model_config = ConfigDict(frozen=True)

    story: ToldStory[FollowedStep]
    round: int = Field(ge=FIRST_ROUND)
    # The take of the change its pieces were cut out of
    take: int = Field(ge=FIRST_TAKE)
    # Set while the code under it moved on after it was told: a step shows
    # other code than it was told with, or more is left out than was
    moved_on: CodeMovedOn | None


class _StoryKept(BaseModel):
    """A story told, kept both ways at once: as it was told, and as it is held on the take on screen."""

    model_config = ConfigDict(frozen=True)

    # What every take after the one it was told of follows it from: its
    # pieces are what each step was told with
    told: ToldStory[ToldStep]
    # The story told until the diff is taken again; followed onto each take after
    held: StoryHeld


class ReviewStory:
    """The story told of the review's change, the last told in place of any before, and the asking for one until then.

    What changes the asking — the reader asks, an agent takes the request,
    the reader stops it — answers with the asking as it then stands, or
    with None where it changed nothing.
    """

    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        # None while nobody has told one
        self._kept: _StoryKept | None = None
        # From the reader's request until a story is told; None while nothing is asked
        self._asking: StoryAsking | None = None
        # Stories that arrive together are told one after another, as they
        # arrived: told side by side, a long one sent first would finish last
        # and take the place of the one sent after it
        self._telling = asyncio.Lock()

    @property
    def held(self) -> StoryHeld | None:
        """The story held, on the take of the change on screen: None while nobody has told one."""
        return None if self._kept is None else self._kept.held

    @property
    def asking(self) -> StoryAsking | None:
        """How the reader's asking for a story stands: None while nothing is asked, and once a story is held."""
        return self._asking

    def ask(self) -> StoryAsking | None:
        """Begin the reader's asking for a story, now, unless the story held is current or one is still awaited.

        A story held is current until a round moves the code on under it:
        then it is asked for again, to be told of the code as it stands.
        Asked again after the reader stopped it, the asking begins anew.
        """
        held = self.held
        if (held is not None and held.moved_on is None) or self._awaited is not None:
            return None
        self._asking = StoryAsking(asked_at=self._clock.now(), taken_at=None, stopped=False)
        return self._asking

    def taken(self) -> StoryAsking | None:
        """Note that an agent took the request for the story awaited, now."""
        awaited = self._awaited
        if awaited is None or awaited.taken_at is not None:
            return None
        self._asking = awaited.taken(self._clock.now())
        return self._asking

    def stop(self) -> StoryAsking | None:
        """Note that the reader stopped the story awaited: one told after all is still taken."""
        awaited = self._awaited
        if awaited is None:
            return None
        self._asking = awaited.stopped_by_the_reader()
        return self._asking

    async def tell(self, story: Story[Step], change: ReviewContent, *, round_number: int) -> StoryHeld:
        """Tell a story of a take of the change and hold it, in place of any told before, with the round it arrived in.

        Told off the event loop: a story of a large change takes seconds to
        place on it, and the server has every page's socket and the agent's
        wait to keep answering meanwhile. Held, it ends the asking for one,
        stopped or not.

        Raises:
            StoryRefusedError: if anything is wrong with the story, carrying all of it; the story held stays,
                and so does the asking.
        """
        async with self._telling:
            told = await asyncio.to_thread(story_telling.tell, story, change.files)
            held = StoryHeld(story=story_telling.as_told(told), round=round_number, take=change.take, moved_on=None)
            self._kept = _StoryKept(told=told, held=held)
            self._asking = None
            return held

    async def follow(self, change: ReviewContent, *, round_number: int) -> None:
        """Follow the story told onto a later take of the change, taken again in this round; with none told, nothing.

        Off the event loop and in turn with tellings, as a story is told: a
        story told while the diff was taken again is followed once it is held.
        """
        async with self._telling:
            kept = self._kept
            if kept is None:
                return
            followed = await asyncio.to_thread(story_telling.follow, kept.told, change.files)
            held = StoryHeld(
                story=followed,
                round=kept.held.round,
                take=change.take,
                moved_on=_moved_on(kept.told, followed, moved_on_before=kept.held.moved_on, round_number=round_number),
            )
            self._kept = _StoryKept(told=kept.told, held=held)

    def went_stale(self) -> StoryWentStale | None:
        """What went stale of the story held, as it stands now: None while it is current, or none is held."""
        held = self.held
        if held is None or held.moved_on is None:
            return None
        return StoryWentStale(
            round=held.moved_on.round,
            steps=[
                StaleStep(chapter=chapter.id, file=step.file, lines=None if step.now is None else step.now.lines)
                for chapter in held.story.chapters
                for step in chapter.steps
                if not step.stands_as_told
            ],
            left_out=_changed_lines_left_out(held.story),
        )

    @property
    def _awaited(self) -> StoryAsking | None:
        """The asking the reader still waits on: None where they asked for nothing, or stopped it."""
        if self._asking is None or self._asking.stopped:
            return None
        return self._asking


def _moved_on(
    told: ToldStory[ToldStep],
    followed: ToldStory[FollowedStep],
    *,
    moved_on_before: CodeMovedOn | None,
    round_number: int,
) -> CodeMovedOn | None:
    """That the round's work moved the code on under the story, if it did: a step changed, or more is left out.

    Fewer lines left out than when it was told is no reason: what the round
    took out of the change leaves the story as true as it was. It moved on
    in the round a take first found it so: the take before says which, where
    it left the story moved on too.
    """
    left_out_when_told = _changed_lines_left_out(told)
    left_out_now = _changed_lines_left_out(followed)
    all_as_told = all(step.stands_as_told for chapter in followed.chapters for step in chapter.steps)
    if all_as_told and left_out_now <= left_out_when_told:
        return None
    first_round = round_number if moved_on_before is None else moved_on_before.round
    return CodeMovedOn(round=first_round, left_out=_left_out_changed(left_out_when_told, left_out_now))


def _left_out_changed(when_told: int, now: int) -> LeftOutChanged | None:
    """How many changed lines no step tells then and now, where they differ: None where they do not."""
    return None if now == when_told else LeftOutChanged(when_told=when_told, now=now)


def _changed_lines_left_out[StepKind: Step](story: ToldStory[StepKind]) -> int:
    """How many lines the change added or removed that no step of the story tells."""
    return sum(left.changed_lines for left in story.left_out)
