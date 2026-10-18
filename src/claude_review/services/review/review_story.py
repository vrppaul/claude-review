"""The story a review holds: the last one the agent told of its change, on the take of it on screen.

A story is told of the change as it stood, and kept as it was told, with
the round it was told in, until the next telling replaces it whole. The
round's work then moves the code under it, and each take of the change the
review makes, the story told is followed onto: the story held is that one,
showing the code as it now stands and saying whether it moved on. It is
always followed from the story as it was told, whose pieces are what each
step was told with, through what git says changed from the tree the take it
was told of was written down as to the later take's. Its pieces are cut
out of one take of the change, so it says which: a page that read the diff
of a later take can tell that they are not yet of the code it shows.

A story is asked for by the reader, or by the review itself where the
reader wants stories. That asking is kept here, beside the story that ends
it: when it was asked, when an agent took the request, whether the reader
stopped it. A story is asked for only while no story held is current —
none is held, or a round moved the code on under it — and none is awaited,
so however many pages are open, and however often, the review is asked
once.
"""

import asyncio
from typing import override

import structlog
from pydantic import BaseModel, ConfigDict

from claude_review.domain.exceptions import NoRepositoryError
from claude_review.domain.interfaces import Clock, GitError
from claude_review.domain.models import DiffFile, StaleStep, StoryRequested, StoryWentStale
from claude_review.domain.story import (
    CodeMovedOn,
    FollowedStep,
    LeftOutChanged,
    Step,
    Story,
    StoryAsking,
    StoryHeld,
    ToldStep,
    ToldStory,
)
from claude_review.services import story_telling
from claude_review.services.review.agent_inbox import StandingRequest
from claude_review.services.review.review_content import ReviewContent, TakesCompared

log = structlog.get_logger()

# What a review of files read once, or of a conversation, says to a story told of it, and to the asking for one
NO_CHANGE_TO_TELL = "This review is of no change: its content came from no repository"


class _StoryKept(BaseModel):
    """A story told, kept both ways at once: as it was told, and as it is held on the take on screen."""

    model_config = ConfigDict(frozen=True)

    # What every take after the one it was told of follows it from: its
    # pieces are what each step was told with
    told: ToldStory[ToldStep]
    # The tree the take it was told of was written down as, which each later
    # take is compared with: None where git wrote none
    told_on: str | None
    # The story told until the diff is taken again; followed onto each take after
    held: StoryHeld


class ReviewStory(StandingRequest):
    """The story told of the review's change, the last told in place of any before, and the asking for one until then.

    The one owner of a story being wanted. It asks for one itself where the
    reader wants stories, one can be told of this review, and none is held
    current, asked for or stopped by the reader: as the review opens, once
    a retake leaves the story held stale, and when stories are turned on.
    Whether they are on is the reader's setting, kept for every review on
    the machine: it is handed in at each of those moments, never kept here,
    so a change made in another review is acted on at this review's next
    one. An agent's wait claims the asking (`claim`); nothing of it waits in
    the agent's inbox, which keeps only what someone said.

    What changes the asking — it is asked, an agent takes it, the reader
    stops it — answers with the asking as it then stands, or with None
    where it changed nothing.

    Whether a story can be told of this review at all is its own to say
    (`takes_a_story`): where none can, a story told and the reader's asking
    for one are refused, and stories turned on ask for none.
    """

    def __init__(self, clock: Clock, takes: TakesCompared, *, takes_a_story: bool) -> None:
        self._clock = clock
        # What says how the code moved between the take a story was told of and a later one
        self._takes = takes
        # Whether a story can be told of this review: its content is a change to a repository
        self._takes_a_story = takes_a_story
        # None while nobody has told one
        self._kept: _StoryKept | None = None
        # From the asking until a story is told; None while nothing is asked
        self._asking: StoryAsking | None = None
        # Set while the asking waits for an agent to take it: what wakes an agent's wait
        self._due = asyncio.Event()
        # Stories that arrive together are told one after another, as they
        # arrived: told side by side, a long one sent first would finish last
        # and take the place of the one sent after it
        self._telling = asyncio.Lock()

    @property
    def takes_a_story(self) -> bool:
        """Whether a story can be told of this review: of a change somebody made, never of files or a conversation."""
        return self._takes_a_story

    @property
    def held(self) -> StoryHeld | None:
        """The story held, on the take of the change on screen: None while nobody has told one."""
        return None if self._kept is None else self._kept.held

    @property
    def asking(self) -> StoryAsking | None:
        """How the reader's asking for a story stands: None while nothing is asked, and once a story is held."""
        return self._asking

    @property
    @override
    def due(self) -> asyncio.Event:
        return self._due

    def ask(self) -> StoryAsking | None:
        """The reader asking for a story: begun now, unless the story held is current or one is still awaited.

        Raises:
            NoRepositoryError: if no story can be told of this review: files read once, or a conversation.
        """
        self._require_a_change()
        return self._begun()

    def want(self, *, stories_on: bool) -> StoryAsking | None:
        """Ask for a story where the reader wants stories and none is asked: never over one the reader stopped.

        They stopped it to keep the agent's tokens: only turning stories on
        again asks once more.
        """
        if not stories_on or self._asking is not None:
            return None
        return self._begun()

    def stories_turned(self, *, on: bool) -> StoryAsking | None:
        """The reader turned stories on or off: on asks for this review's story, off stops one awaited."""
        return self._begun() if on else self.stop()

    @override
    def claim(self) -> StoryRequested | None:
        """Hand the story awaited to an agent, noted as taken now: None where none waits to be taken.

        It says what went stale of the story held, as that stands now.
        """
        awaited = self._awaited
        if awaited is None or awaited.taken_at is not None:
            return None
        self._noted(awaited.taken(self._clock.now()))
        return StoryRequested(stale=self.went_stale())

    def stop(self) -> StoryAsking | None:
        """Note that the reader stopped the story awaited: one told after all is still taken."""
        awaited = self._awaited
        if awaited is None:
            return None
        return self._noted(awaited.stopped_by_the_reader())

    async def tell(self, story: Story[Step], change: ReviewContent, *, round_number: int) -> StoryHeld:
        """Tell a story of a take of the change and hold it, in place of any told before, with the round it arrived in.

        Told off the event loop: a story of a large change takes seconds to
        place on it, and the server has every page's socket and the agent's
        wait to keep answering meanwhile. Held, it ends the asking for one,
        stopped or not.

        Raises:
            NoRepositoryError: if no story can be told of this review: files read once, or a conversation.
            StoryRefusedError: if anything is wrong with the story, carrying all of it; the story held stays,
                and so does the asking.
        """
        self._require_a_change()
        async with self._telling:
            told = await asyncio.to_thread(story_telling.tell, story, change.files)
            held = StoryHeld(story=story_telling.as_told(told), round=round_number, take=change.take, moved_on=None)
            self._kept = _StoryKept(told=told, told_on=change.written_as, held=held)
            self._noted(None)
            return held

    async def follow(self, change: ReviewContent, *, round_number: int, stories_on: bool) -> StoryAsking | None:
        """Follow the story told onto a later take of the change, taken again in this round, and ask for one if due.

        Off the event loop and in turn with tellings, as a story is told: a
        story told while the diff was taken again is followed once it is held,
        compared from the very take it was told of. Whether a story is then
        wanted is asked after that, so a story that arrived during the retake
        and ended the asking is asked for again if the retake left it stale.
        Answers with the asking begun, or None.
        """
        async with self._telling:
            await self._followed(change, round_number=round_number)
            return self.want(stories_on=stories_on)

    async def _followed(self, change: ReviewContent, *, round_number: int) -> None:
        """Follow the story told, if any, onto a later take of the change, taken again in this round."""
        kept = self._kept
        if kept is not None:
            since_told = await self._changed_since(kept.told_on, change.written_as)
            followed = await asyncio.to_thread(story_telling.follow, kept.told, change.files, since_told)
            held = StoryHeld(
                story=followed,
                round=kept.held.round,
                take=change.take,
                moved_on=_moved_on(kept.told, followed, moved_on_before=kept.held.moved_on, round_number=round_number),
            )
            self._kept = _StoryKept(told=kept.told, told_on=kept.told_on, held=held)

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

    async def _changed_since(self, told_on: str | None, now_on: str | None) -> list[DiffFile] | None:
        """What changed from the take a story was told of to a later one: None where either tree, or git, is wanting.

        Then no step can be placed, and none is, rather than one guessed at.
        """
        if told_on is None or now_on is None:
            return None
        try:
            return await self._takes.changed_between(told_on, now_on)
        except GitError as refusal:
            log.warning("takes_not_compared", reason=str(refusal))
            return None

    def _require_a_change(self) -> None:
        """Refuse what only a review of a change can do: tell a story, or ask for one.

        Raises:
            NoRepositoryError: if no story can be told of this review: files read once, or a conversation.
        """
        if not self._takes_a_story:
            raise NoRepositoryError(NO_CHANGE_TO_TELL)

    def _begun(self) -> StoryAsking | None:
        """Begin asking for a story, now, where one can be told and no story held is current or awaited.

        What the reader asking does, the review wanting one, and turning
        stories on. A story held is current until a round moves the code on
        under it: then it is asked for again, to be told of the code as it
        stands. Asked again after the reader stopped it, the asking begins anew.
        """
        if not self._takes_a_story or self._is_current or self._awaited is not None:
            return None
        return self._noted(StoryAsking(asked_at=self._clock.now(), taken_at=None, stopped=False))

    @property
    def _awaited(self) -> StoryAsking | None:
        """The asking the reader still waits on: None where they asked for nothing, or stopped it."""
        if self._asking is None or self._asking.stopped:
            return None
        return self._asking

    @property
    def _is_current(self) -> bool:
        """Whether a story is held that no round has moved the code on under since it was told."""
        held = self.held
        return held is not None and held.moved_on is None

    def _noted(self, asking: StoryAsking | None) -> StoryAsking | None:
        """Hold the asking as it now stands, and say an agent's wait may claim it exactly while it waits to be taken."""
        self._asking = asking
        awaited = self._awaited
        if awaited is not None and awaited.taken_at is None:
            self._due.set()
        else:
            self._due.clear()
        return asking


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
