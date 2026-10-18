"""One review, whole: everything it holds, and everything that happens to it, in one owner.

The review is read in a page and answered by an agent in another process,
and the two never talk to each other directly. Everything one hands the
other passes through here: what the reader asks lands in the agent's inbox,
what the agent says is told to every page on screen, and what the review
holds — its content, its rounds, the threads the page described — is kept
by the part that answers for it.

`Review` is made of those parts, each the one keeper of its own:
`ReviewLifetime` of when the review ends and why, `BrowserPresence` of
whether it is on the reader's screen, `Answerer` of the agent answering it,
`AgentInbox` of what the reader handed over for the agent, `RoundTracker`
of which round is being written, `Conversation` of what was said in the
panel, `ReaderThreads` of the threads the page holds, `ReviewStory` of the
story told of its change and of the reader's asking for one, and the
`ContentSource` of where its content comes from. That one is handed in:
its host picks it by what was opened, so a review of files is never handed
git, and the review reads what it was opened on from it. `ThreadHandover`
makes a thread's screenshots files the agent may open, and a
`RoundFormatter`, chosen once for the kind of review, writes a round as it
is sent.
"""

from collections.abc import Awaitable
from contextlib import AbstractContextManager

import structlog

from claude_review.domain.exceptions import ReviewEndedError, UnknownFileError
from claude_review.domain.interfaces import Clock, PageChannel, RecordChange
from claude_review.domain.models import (
    AgentEvent,
    AgentWork,
    Anchor,
    CommentSeverity,
    FilePath,
    PanelCancel,
    PanelEntry,
    PanelMessage,
    ProgressStep,
    ReaderSettings,
    RoundSubmission,
    SaidInPanel,
    StoryCancelled,
    StoryRequested,
    Thread,
    ThreadDraft,
    ThreadQuestion,
    TurnAuthor,
    VersionKey,
    VersionOnOffer,
)
from claude_review.domain.page_events import (
    AgentSaid,
    DiffRetaken,
    FileShown,
    RoundBegan,
    StoryAskingChanged,
    StoryTold,
    ThreadAnswered,
    ThreadRaised,
    TreeMoved,
)
from claude_review.domain.story import Step, Story, StoryAsking, StoryHeld
from claude_review.services.anchor_service import AnchorService, StoryAnchorHandler
from claude_review.services.exit_report import exit_report
from claude_review.services.file_window_service import FileWindow
from claude_review.services.image_service import ImageService, StoredImage
from claude_review.services.place_words import place_in_words
from claude_review.services.reader_record_service import ReaderRecordService
from claude_review.services.review.agent_inbox import AgentInbox, Silence
from claude_review.services.review.answerer import ANSWERER_LEASE_SECONDS, Answerer
from claude_review.services.review.browser_presence import RELOAD_GRACE_SECONDS, BrowserPresence
from claude_review.services.review.content_sources import ContentSource, DiffView, Retaken
from claude_review.services.review.conversation import Conversation
from claude_review.services.review.reader_threads import ReaderThreads
from claude_review.services.review.review_lifetime import EndReason, ReviewLifetime
from claude_review.services.review.review_story import ReviewStory
from claude_review.services.review.round_tracker import RoundTracker
from claude_review.services.review.standing import CatchUp, ReviewStanding
from claude_review.services.review.thread_handover import ThreadHandover
from claude_review.services.round_formatter import RoundFormatter

log = structlog.get_logger()


class Review:
    """One review: its content, its rounds, its conversation, and the two sides it passes between."""

    def __init__(
        self,
        source: ContentSource,
        *,
        page: PageChannel,
        clock: Clock,
        images: ImageService,
        settings: ReaderRecordService[ReaderSettings],
    ) -> None:
        # What it was opened on, read from the source made from it: handed once, it cannot be another's
        opening = source.opening
        self._mode = opening.mode
        self._title = opening.title
        self._identity = opening.identity_digest
        self._opened_against = opening.opened_against
        self._page = page
        self._images = images
        self._presence = BrowserPresence(reload_grace=RELOAD_GRACE_SECONDS)
        self._lifetime = ReviewLifetime(page)
        self._rounds = RoundTracker()
        self._answerer = Answerer(page, clock, lease_seconds=ANSWERER_LEASE_SECONDS)
        self._conversation = Conversation(clock)
        self._threads = ReaderThreads()
        self._handover = ThreadHandover(images)
        self._source = source
        self._story = ReviewStory(clock, takes=source, takes_a_story=source.is_a_change)
        self._inbox = AgentInbox(self._lifetime, standing=self._story)
        # The reader's choices, kept for every review on the machine: read
        # where one decides something here, never copied, since another
        # review may change them at any moment
        self._settings = settings
        # Chosen once: a review of a conversation quotes what each comment is
        # on, since the agent will not have the conversation in front of it
        self._formatter = RoundFormatter.for_mode(opening.mode)

    @property
    def lifetime(self) -> ReviewLifetime:
        """Whether the review is still running: what whoever hosts it runs its parts until."""
        return self._lifetime

    def standing(self) -> ReviewStanding:
        """What the review is and where it has got to, in one piece."""
        return ReviewStanding(
            title=self._title,
            identity=self._identity,
            mode=self._mode,
            opened_against=self._opened_against,
            round=self._rounds.current,
            answerer_attached=self._answerer.attached,
            agent=self._answerer.status,
            takes_a_story=self._story.takes_a_story,
            story_asking=self._story.asking,
        )

    def catch_up(self) -> CatchUp:
        """What an agent arriving late is told: an index of the review, nothing handed over."""
        return CatchUp(
            standing=self.standing(),
            file_count=len(self._source.content.files),
            threads=self._threads.held,
            panel=[self._as_an_agent_reads(said) for said in self._conversation.said],
        )

    def conversation_held(self) -> list[SaidInPanel]:
        """What was said in the panel, oldest first: what a page opening draws, whatever its draft holds."""
        return self._conversation.said

    def answers_to(self, identity: str) -> bool:
        """Whether a page naming this identity reads this review, rather than one that ran on its port before."""
        return identity == self._identity

    def page_open(self) -> AbstractContextManager[None]:
        """Count a page as open on the review for as long as this lasts."""
        return self._presence.page_open()

    def page_reached_round(self, number: int) -> None:
        """Take the round a page says it had got to, never going back."""
        self._rounds.catch_up(number)

    def page_holds(self, threads: list[ThreadDraft], unreadable_ids: list[str]) -> None:
        """Take the threads a page says it holds, and the ids of those it could not say."""
        self._threads.hold(threads, unreadable_ids)

    def threads_held(self) -> list[ThreadDraft]:
        """The threads the review holds: as a page last said them, and the agent's own however a page left them."""
        return self._threads.held

    def agent_called(self) -> None:
        """Note that the agent is still there: every call it makes renews its lease."""
        self._answerer.heard()

    def report_work(
        self, *, message_id: str | None, text: str, files: list[FilePath], steps: list[ProgressStep]
    ) -> None:
        """Say what the agent is doing, replacing whatever was showing; nothing said ends it.

        The files are any the agent names, the diff holding them or not: it
        works on files it is about to make, and the page says of each it
        cannot take the reader to that it is not in the diff yet.
        """
        self._answerer.report_work(message_id=message_id, text=text, files=files, steps=steps)

    def report_status(self, *, model: str | None, context: str | None) -> None:
        """Take what the agent says about itself."""
        self._answerer.report_status(model=model, context=context)

    async def keep_image(self, content: bytes) -> StoredImage:
        """Keep an image the reader is about to send."""
        stored = await self._images.keep(content)
        log.info("image_kept", image_id=stored.image_id, size=stored.size)
        return stored

    def kept_image(self, image_id: str) -> StoredImage:
        """An image this review keeps."""
        return self._images.kept(image_id)

    async def discard_image(self, image_id: str) -> None:
        """Drop an image the reader took off before sending it."""
        await self._images.discard(image_id)
        log.info("image_discarded", image_id=image_id)

    async def discard_unsent_images(self) -> None:
        """Once the review has ended, drop every image the reader pasted and never sent: nobody will send it now."""
        await self._images.discard_unsent()

    async def view(self, base: VersionKey | None, *, ignore_whitespace: bool) -> DiffView:
        """The diff against a base the review offers, its own when None."""
        return await self._source.view(base, ignore_whitespace=ignore_whitespace)

    async def offer(self) -> list[VersionOnOffer]:
        """The bases the diff can be read against."""
        return await self._source.offer()

    async def file_window(self, path: str, start: int, end: int) -> FileWindow:
        """Lines a hunk left out, so the reader can widen its context."""
        return await self._source.file_window(path, start, end)

    def follow(self, anchors: list[Anchor]) -> list[Anchor]:
        """Where each anchor is in the content and the story as they now stand, or marked outdated."""
        found = self._anchors
        return [found.follow(anchor) for anchor in anchors]

    async def open(self) -> None:
        """Note what the review opens on, before any page or agent can reach it, and ask for its story if wanted."""
        await self._source.open(self._rounds)
        self._tell_asking(self._story.want(stories_on=await self._stories_on()))

    def work_under_way(self) -> AgentWork | None:
        """What the agent says it is doing now, if anything: a page opening, or coming back, learns it here."""
        return self._answerer.work

    async def next_event(self, *, within: float, caller_left: Awaitable[None]) -> AgentEvent | Silence:
        """The next thing the reader handed over, for the agent asking.

        Waiting is what says most plainly that an agent is there, which is
        what makes rounds worth offering in the review. A story asked for is
        handed over once nothing the reader said waits, and says what went
        stale of the story held as the agent takes it: the last retake before
        then is what it is told of.
        """
        with self._answerer.waiting():
            taken = await self._inbox.take(within=within, caller_left=caller_left)
            # Told the pages with no await since the story was claimed: the reader's stopping finds the
            # request either still waiting or noted as taken, never between
            if isinstance(taken, StoryRequested):
                self._tell_asking(self._story.asking)
                log.info("story_request_taken")
            return taken

    def ask(self, question_id: str, thread: ThreadDraft) -> None:
        """Take a question asked in one thread, for the agent to pick up.

        Raises:
            QuestionNotInThreadError: if the question names nothing the reader said in the thread.
            AnchorLinesNotShownError: if the thread names lines it does not quote.
            AgentWordsChangedError: if it is the agent's own thread, and no longer opens as the agent raised it.
        """
        asked = thread.part_asked(question_id)
        self._check_threads([thread])
        handed = self._hand_over(thread)
        # Handed over with the thread already; named again, they are the same
        # files. Like every image in the thread, one this review no longer keeps
        # is left out: after a restart a screenshot is gone however recently it
        # was pasted, and nothing here can tell the two apart.
        images = self._handover.kept_images(asked.images)
        self._inbox.hand_in(ThreadQuestion(question_id=question_id, body=asked.body, images=images, thread=handed))
        log.info("thread_question", thread_id=thread.thread_id, where=place_in_words(handed.anchor))

    def take_message(self, *, message_id: str, body: str, threads: list[ThreadDraft], image_ids: list[str]) -> None:
        """Take what the reader typed in the panel, for the agent to pick up.

        Raises:
            ImagesNotKeptError: if it names an image this review does not keep.
            AnchorLinesNotShownError: if a thread it points at names lines it does not quote.
            AgentWordsChangedError: if a thread it points at is the agent's own, and no longer opens as it raised it.
        """
        self._check_threads(threads)
        # Pasted a moment ago, so an image this review does not keep is a fault
        # to report, not a screenshot to leave out quietly. Checked before any
        # is handed over, so a refused message leaves none of them kept for good.
        self._images.require(image_ids)
        handed = self._images.hand_over(image_ids).paths
        self._answerer.message_arrived()
        self._inbox.hand_in(
            PanelMessage(
                message_id=message_id,
                body=body,
                threads=[self._hand_over(thread) for thread in threads],
                images=handed,
            )
        )
        self._conversation.reader_said(
            message_id=message_id, body=body, images=image_ids, threads=[thread.thread_id for thread in threads]
        )
        log.info("panel_message", message_id=message_id, threads=len(threads), images=len(handed))

    def take_back(self, message_id: str) -> None:
        """Take back a message the agent has not answered yet: a request it picks up, not a kill."""
        self._inbox.hand_in(PanelCancel(message_id=message_id))
        self._answerer.end_work_for(message_id)
        self._conversation.taken_back(message_id)
        log.info("panel_cancelled", message_id=message_id)

    def agent_says(self, *, message_id: str | None, body: str, files: list[FilePath]) -> None:
        """Tell the pages what the agent says in the panel: an answer to a message, or the agent speaking first.

        The files are any the agent names, as the work it reports names them.
        """
        said_id = self._conversation.agent_said(message_id=message_id, body=body, files=files)
        self._page.tell(AgentSaid(said_id=said_id, message_id=message_id, body=body, files=files))
        self._answerer.end_work_for(message_id)
        log.info("panel_answer", message_id=message_id, unprompted=message_id is None)

    def answer_thread(self, *, thread_id: str, question_id: str | None, body: str) -> None:
        """Tell the pages the answer to a question asked in a thread.

        Raises:
            UnknownThreadError: if the review never heard of the thread: no page would show the answer.
        """
        self._threads.require(thread_id)
        self._page.tell(ThreadAnswered(thread_id=thread_id, question_id=question_id, body=body))
        log.info("thread_reply", thread_id=thread_id, question_id=question_id)

    def show(self, file: FilePath) -> None:
        """Take the reader to a file, which they asked to be taken to.

        Raises:
            UnknownFileError: if the review holds no such file: the page would take them nowhere.
        """
        if file not in self._source.content.paths:
            msg = f"{file} is not in this review"
            raise UnknownFileError(msg)
        self._page.tell(FileShown(file=file))
        log.info("file_shown", file=file)

    def raise_thread(self, anchor: Anchor, *, body: str, severity: CommentSeverity) -> str:
        """Put the agent's own thread on what the anchor names, and say its id.

        The anchor is checked against the content on screen and quoted from
        it, because the quote is what lets the thread find its code again.

        Raises:
            UnknownAnchorFileError, AnchorLinesNotShownError, AnchorTooLongError:
                if the anchor names something the content does not show.
            UnknownStoryBlockError: if it names a block of words the story told does not say.
        """
        quoted = self._anchors.quote(anchor)
        thread_id = self._threads.raise_id()
        self._threads.raised(
            ThreadDraft(
                thread_id=thread_id,
                anchor=quoted,
                severity=severity,
                body=body,
                images=[],
                turns=[],
                raised_by=TurnAuthor.AUTHOR,
                resolved=False,
            )
        )
        self._page.tell(ThreadRaised(thread_id=thread_id, anchor=quoted, body=body, severity=severity))
        log.info("thread_raised", thread_id=thread_id, where=place_in_words(quoted))
        return thread_id

    def read_thread(self, thread_id: str) -> Thread:
        """Hand over one thread the page holds, in full: read, its images are the agent's to open from now on.

        Raises:
            UnknownThreadError: if the page holds no such thread.
        """
        return self._hand_over(self._threads.find(thread_id))

    def submit(self, *, threads: list[ThreadDraft], body: str | None, ends: bool) -> RoundSubmission:
        """Send what has been written as a round, and either end the review or carry on to the next round.

        Raises:
            ReviewEndedError: if the review has already ended.
            AnchorLinesNotShownError: if a thread names lines it does not quote.
            AgentWordsChangedError: if a thread the agent raised no longer opens as it raised it.
        """
        if self._lifetime.has_ended:
            msg = "Review already submitted"
            raise ReviewEndedError(msg)
        self._check_threads(threads)

        number = self._rounds.current
        result = self._formatter.format(
            [self._hand_over(thread) for thread in threads],
            body,
            round_number=number,
            anchors=self._anchors,
        )
        submission = RoundSubmission(number=number, markdown=result.markdown, comment_count=result.comment_count)
        self._rounds.sent(submission)
        self._inbox.hand_in(submission)

        if ends:
            self._lifetime.end(EndReason.FINISHED)
        else:
            self._page.tell(RoundBegan(number=self._rounds.begin_next()))

        log.info("review_submitted", comment_count=result.comment_count, round=number, ended=ends)
        return submission

    async def tell_story(self, story: Story[Step]) -> StoryHeld:
        """Take the story the agent tells of the change, whole, in place of any it told before.

        Told of the review's own diff as it stands when the story arrives,
        whatever base a page reads, and kept with the round it arrived in
        and the take it was told of. Every page open is told there is one,
        and reads it from here; then that it ended the reader's asking for
        one, asked for or not, stopped or not.

        Raises:
            NoRepositoryError: if the review is of no change: files read once, or a conversation.
            StoryRefusedError: if anything is wrong with the story, carrying all of it.
        """
        held = await self._story.tell(story, self._source.content, round_number=self._rounds.current)
        # The asking ended as the story came to be held, with no await since: a stop no agent took would hand
        # the next one a story to stop writing
        self._inbox.withdraw(StoryCancelled())
        self._page.tell(StoryTold())
        self._page.tell(StoryAskingChanged(asking=self._story.asking))
        log.info(
            "story_told",
            chapters=len(held.story.chapters),
            left_out=len(held.story.left_out),
            round=held.round,
            take=held.take,
        )
        return held

    def ask_for_story(self) -> None:
        """Take the reader's asking for a story of the change, for an agent to pick up, and tell the pages it is asked.

        Asked once however often it is said: while a story is awaited, or
        the one held is current, nothing changes. Over a story a round moved
        the code on under, it asks for that story told again. With no agent
        there the request waits for the first that asks, once nothing the
        reader said is left for it.

        Raises:
            NoRepositoryError: if the review is of no change: files read once, or a conversation.
        """
        self._tell_asking(self._story.ask())

    def stop_story(self) -> None:
        """Stop the story the reader asked for, and tell the pages it is stopped; with none awaited, nothing changes.

        A request no agent took is taken back, and no agent hears of it or
        of its stopping. One an agent took cannot be: the agent is handed
        the word to stop, and decides what to do about it.
        """
        self._story_stopped(self._story.stop())

    async def change_settings(self, change: RecordChange[ReaderSettings]) -> ReaderSettings:
        """Keep a choice the reader made, for this review and every later one, and act on it here.

        Stories turned on ask for this review's story wherever none is
        current or awaited, one the reader stopped included; turned off,
        they stop one awaited. A change made in another review on the
        machine is acted on at this review's next decision point: a retake,
        or a change made here.
        """
        before = await self._kept_settings()
        changed = await self._settings.change(change)
        if changed.stories != before.stories:
            turned = self._story.stories_turned(on=changed.stories)
            if changed.stories:
                self._tell_asking(turned)
            else:
                self._story_stopped(turned)
        return changed

    def story_held(self) -> StoryHeld | None:
        """The story the review holds, on the take of its change on screen: None while nobody has told one."""
        return self._story.held

    async def retake(self) -> Retaken:
        """Take the diff again, after the work a round asked for, follow the story told onto it, and tell the pages.

        The source takes one retake at a time and reads the round from the
        review's rounds once its turn comes, so a round sent while git works
        is not its round. Followed before the pages are told, so a page that
        reads the diff and then the story reads both of one take.

        Raises:
            NoRepositoryError: if the review's content did not come from a repository.
        """
        retaken = await self._source.retake(self._rounds)
        content, stories_on = self._source.content, await self._stories_on()
        self._tell_asking(await self._story.follow(content, round_number=retaken.round, stories_on=stories_on))
        self._page.tell(DiffRetaken(file_count=retaken.file_count, changes=retaken.changes))
        return retaken

    def end(self) -> None:
        """End a review that was kept open for rounds."""
        self._lifetime.end(EndReason.FINISHED)

    async def end_once_its_page_is_closed(self) -> None:
        """End the review once its page is closed rather than reloaded: for everyone, an agent waiting included."""
        if await self._lifetime.before_the_end(self._presence.until_closed_for_good()):
            self._lifetime.end(EndReason.BROWSER_CLOSED)

    async def tell_when_the_tree_moves(self) -> None:
        """Tell the pages each time the tree stops matching the diff, from the first page on, until the review ends.

        Said, never acted on: the reader decides when to take the diff again.
        """
        if await self._lifetime.before_the_end(self._presence.until_first_page()):
            async for moved in self._source.tree_moves(self._lifetime):
                self._page.tell(TreeMoved(moved_count=moved))

    def exit_report(self) -> str:
        """What the review hands back as it ends: its rounds, and whatever the agent never took."""
        return exit_report(self._rounds.last_sent, self._inbox.drain())

    def _tell_asking(self, asking: StoryAsking | None) -> None:
        """Tell the pages how the asking for a story now stands, where it changed."""
        if asking is not None:
            self._page.tell(StoryAskingChanged(asking=asking))
            log.info("story_asking_changed", taken=asking.taken_at is not None, stopped=asking.stopped)

    def _story_stopped(self, stopped: StoryAsking | None) -> None:
        """Tell the pages a story awaited was stopped, and the agent too where it had taken the request already.

        A request no agent took goes to none once stopped. One an agent took
        cannot be taken back: the agent is handed the word to stop, and
        decides what to do about it.
        """
        if stopped is None:
            return
        if stopped.taken_at is not None:
            self._inbox.hand_in(StoryCancelled())
        self._page.tell(StoryAskingChanged(asking=stopped))
        log.info("story_stopped")

    async def _stories_on(self) -> bool:
        """Whether the reader wants a story of every change, as their settings say now."""
        return (await self._kept_settings()).stories

    async def _kept_settings(self) -> ReaderSettings:
        """The reader's settings as kept now, or what a reader who never chose gets."""
        return await self._settings.read() or self._settings.defaults()

    def _check_threads(self, threads: list[ThreadDraft]) -> None:
        """Refuse threads the agent cannot be handed as they are, before any of them is handed over with its images.

        Raises:
            AnchorLinesNotShownError: if one names lines it does not quote.
            AgentWordsChangedError: if one the agent raised no longer opens as the agent raised it.
        """
        anchors = self._anchors
        for thread in threads:
            anchors.check_quote(thread.anchor)
        self._threads.check_openings(threads)

    @property
    def _anchors(self) -> AnchorService:
        """Every kind of anchor, read against what the review holds now: the take of its content, and the story told."""
        held = self._story.held
        return AnchorService(
            lines=self._source.content.line_anchors, story=StoryAnchorHandler(None if held is None else held.story)
        )

    def _hand_over(self, thread: ThreadDraft) -> Thread:
        """A thread as the agent is handed it, which the agent may answer in from now on."""
        self._threads.handed(thread.thread_id)
        return self._handover.thread(thread)

    def _as_an_agent_reads(self, said: SaidInPanel) -> PanelEntry:
        """Something said in the panel, its screenshots as the files the agent was handed them as when it was sent."""
        kept = [self._images.find(image_id) for image_id in said.images]
        return PanelEntry(
            message_id=said.message_id,
            author=said.author,
            body=said.body,
            at=said.at,
            images=[stored.path for stored in kept if stored is not None],
        )
