"""One review, whole: everything it holds, and everything that happens to it, in one owner.

The review is read in a page and answered by an agent in another process,
and the two never talk to each other directly. Everything one hands the
other passes through here: what the reader asks lands in the agent's inbox,
what the agent says is told to every page on screen, and what the review
holds — its content, its rounds, the threads the page described — is kept
by the part that answers for it.
"""

from collections.abc import Awaitable
from contextlib import AbstractContextManager

import structlog

from claude_review.domain.exceptions import ReviewEndedError
from claude_review.domain.interfaces import Clock, PageChannel, ReviewedRepository
from claude_review.domain.models import (
    AgentEvent,
    AgentWork,
    Anchor,
    CommentSeverity,
    FilePath,
    PanelCancel,
    PanelMessage,
    ProgressStep,
    RoundSubmission,
    Thread,
    ThreadDraft,
    ThreadQuestion,
    VersionKey,
    VersionOnOffer,
)
from claude_review.domain.page_events import (
    AgentSaid,
    DiffRetaken,
    FileShown,
    RoundBegan,
    ThreadAnswered,
    ThreadRaised,
    TreeMoved,
)
from claude_review.services.exit_report import exit_report
from claude_review.services.file_window_service import FileWindow
from claude_review.services.image_service import ImageService, StoredImage
from claude_review.services.place_words import place_in_words
from claude_review.services.review.agent_inbox import AgentInbox, Silence
from claude_review.services.review.answerer import ANSWERER_LEASE_SECONDS, Answerer
from claude_review.services.review.browser_presence import RELOAD_GRACE_SECONDS, BrowserPresence
from claude_review.services.review.content_sources import ContentSource, DiffView, Retaken, content_source
from claude_review.services.review.conversation import Conversation
from claude_review.services.review.reader_threads import ReaderThreads
from claude_review.services.review.review_lifetime import EndReason, ReviewLifetime
from claude_review.services.review.round_tracker import RoundTracker
from claude_review.services.review.standing import CatchUp, ReviewStanding
from claude_review.services.review.thread_handover import ThreadHandover
from claude_review.services.review_opening import ReviewOpening
from claude_review.services.round_formatter import RoundFormatter

log = structlog.get_logger()


class Review:
    """One review: its content, its rounds, its conversation, and the two sides it passes between."""

    def __init__(
        self,
        opening: ReviewOpening,
        *,
        repository: ReviewedRepository,
        images: ImageService,
        page: PageChannel,
        clock: Clock,
    ) -> None:
        self._mode = opening.mode
        self._title = opening.title
        self._opened_against = opening.opened_against
        self._page = page
        self._images = images
        self._presence = BrowserPresence(reload_grace=RELOAD_GRACE_SECONDS)
        self._lifetime = ReviewLifetime()
        self._rounds = RoundTracker()
        self._answerer = Answerer(page, clock, lease_seconds=ANSWERER_LEASE_SECONDS)
        self._inbox = AgentInbox(self._lifetime)
        self._conversation = Conversation(clock)
        self._threads = ReaderThreads()
        self._handover = ThreadHandover(images)
        self._source: ContentSource = content_source(opening, repository=repository, clock=clock, rounds=self._rounds)
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
            mode=self._mode,
            opened_against=self._opened_against,
            round=self._rounds.current,
            answerer_attached=self._answerer.attached,
            agent=self._answerer.status,
        )

    def catch_up(self) -> CatchUp:
        """What an agent arriving late is told: an index of the review, nothing handed over."""
        return CatchUp(
            standing=self.standing(),
            file_count=len(self._source.content.files),
            threads=self._threads.held,
            panel=self._conversation.entries,
        )

    def page_open(self) -> AbstractContextManager[None]:
        """Count a page as open on the review for as long as this lasts."""
        return self._presence.page_open()

    def page_reached_round(self, number: int) -> None:
        """Take the round a page says it had got to, never going back."""
        self._rounds.catch_up(number)

    def page_holds(self, threads: list[ThreadDraft], unreadable_ids: list[str]) -> None:
        """Take the threads a page says it holds, and the ids of those it could not say."""
        self._threads.hold(threads, unreadable_ids)

    def agent_called(self) -> None:
        """Note that the agent is still there: every call it makes renews its lease."""
        self._answerer.heard()

    def report_work(
        self, *, message_id: str | None, text: str, files: list[FilePath], steps: list[ProgressStep]
    ) -> None:
        """Say what the agent is doing, replacing whatever was showing; nothing said ends it."""
        self._answerer.report_work(message_id=message_id, text=text, files=files, steps=steps)

    def report_status(self, *, model: str | None, context: str | None) -> None:
        """Take what the agent says about itself."""
        self._answerer.report_status(model=model, context=context)

    async def keep_image(self, content: bytes) -> StoredImage:
        """Keep an image the reader is about to send."""
        return await self._images.keep(content)

    def kept_image(self, image_id: str) -> StoredImage:
        """An image this review keeps."""
        return self._images.kept(image_id)

    async def discard_image(self, image_id: str) -> None:
        """Drop an image the reader took off before sending it."""
        await self._images.discard(image_id)

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
        """Where each anchor is in the content as it now stands, or marked outdated."""
        found = self._source.content.anchors
        return [found.follow(anchor) for anchor in anchors]

    async def open(self) -> None:
        """Note what the review opens on, before any page or agent can reach it."""
        await self._source.open()

    def work_under_way(self) -> AgentWork | None:
        """What the agent says it is doing now, if anything: a page opening, or coming back, learns it here."""
        return self._answerer.work

    async def next_event(self, *, within: float, caller_left: Awaitable[None]) -> AgentEvent | Silence:
        """The next thing the reader handed over, for the agent asking.

        Waiting is what says most plainly that an agent is there, which is
        what makes rounds worth offering in the review.
        """
        with self._answerer.waiting():
            return await self._inbox.take(within=within, caller_left=caller_left)

    def ask(self, question_id: str, thread: ThreadDraft) -> None:
        """Take a question asked in one thread, for the agent to pick up.

        Raises:
            QuestionNotInThreadError: if the question names nothing the reader said in the thread.
        """
        asked = thread.part_asked(question_id)
        handed = self._handover.thread(thread)
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
        """
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
                threads=[self._handover.thread(thread) for thread in threads],
                images=handed,
            )
        )
        self._conversation.reader_said(message_id=message_id, body=body, images=handed)
        log.info("panel_message", message_id=message_id, threads=len(threads), images=len(handed))

    def take_back(self, message_id: str) -> None:
        """Take back a message the agent has not answered yet: a request it picks up, not a kill."""
        self._inbox.hand_in(PanelCancel(message_id=message_id))
        self._answerer.end_work_for(message_id)
        log.info("panel_cancelled", message_id=message_id)

    def agent_says(self, *, message_id: str | None, body: str, files: list[FilePath]) -> None:
        """Tell the pages what the agent says in the panel: an answer to a message, or the agent speaking first."""
        self._page.tell(AgentSaid(message_id=message_id, body=body, files=files))
        self._answerer.end_work_for(message_id)
        self._conversation.agent_said(message_id=message_id, body=body)
        log.info("panel_answer", message_id=message_id, unprompted=message_id is None)

    def answer_thread(self, *, thread_id: str, question_id: str | None, body: str) -> None:
        """Tell the pages the answer to a question asked in a thread."""
        self._page.tell(ThreadAnswered(thread_id=thread_id, question_id=question_id, body=body))
        log.info("thread_reply", thread_id=thread_id, question_id=question_id)

    def show(self, file: FilePath) -> None:
        """Take the reader to a file, which they asked to be taken to."""
        self._page.tell(FileShown(file=file))
        log.info("file_shown", file=file)

    def raise_thread(self, anchor: Anchor, *, body: str, severity: CommentSeverity) -> str:
        """Put the agent's own thread on what the anchor names, and say its id.

        The anchor is checked against the content on screen and quoted from
        it, because the quote is what lets the thread find its code again.

        Raises:
            UnknownAnchorFileError, AnchorLinesNotShownError, AnchorTooLongError:
                if the anchor names something the content does not show.
        """
        quoted = self._source.content.anchors.quote(anchor)
        thread_id = self._threads.raise_id()
        self._page.tell(ThreadRaised(thread_id=thread_id, anchor=quoted, body=body, severity=severity))
        log.info("thread_raised", thread_id=thread_id, where=place_in_words(quoted))
        return thread_id

    def read_thread(self, thread_id: str) -> Thread:
        """Hand over one thread the page holds, in full: read, its images are the agent's to open from now on.

        Raises:
            UnknownThreadError: if the page holds no such thread.
        """
        return self._handover.thread(self._threads.find(thread_id))

    def submit(self, *, threads: list[ThreadDraft], body: str | None, ends: bool) -> RoundSubmission:
        """Send what has been written as a round, and either end the review or carry on to the next round.

        Raises:
            ReviewEndedError: if the review has already ended.
        """
        if self._lifetime.has_ended:
            msg = "Review already submitted"
            raise ReviewEndedError(msg)

        number = self._rounds.current
        result = self._formatter.format(
            [self._handover.thread(thread) for thread in threads],
            body,
            round_number=number,
            anchors=self._source.content.anchors,
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

    async def retake(self) -> Retaken:
        """Take the diff again, after the work a round asked for, and tell the pages to fetch it.

        Raises:
            NoRepositoryError: if the review's content did not come from a repository.
        """
        retaken = await self._source.retake()
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
