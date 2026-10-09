"""One review, whole: everything it holds, and everything that happens to it, in one owner.

The review is read in a page and answered by an agent in another process,
and the two never talk to each other directly. Everything one hands the
other passes through here: what the reader asks lands in the agent's inbox,
what the agent says is told to every page on screen, and what the review
holds — its content, its rounds, the threads the page described — is kept
by the part that answers for it.
"""

from collections.abc import Awaitable

import structlog

from claude_review.domain.exceptions import ReviewEndedError
from claude_review.domain.models import (
    AgentEvent,
    Anchor,
    CommentSeverity,
    FilePath,
    PanelCancel,
    PanelMessage,
    ReviewMode,
    RoundSubmission,
    Thread,
    ThreadDraft,
    ThreadQuestion,
)
from claude_review.domain.page_events import (
    AgentSaid,
    DiffRetaken,
    FileShown,
    PageEvent,
    RoundBegan,
    ThreadAnswered,
    ThreadRaised,
    WorkReported,
)
from claude_review.domain.protocols import Clock, PageChannel, RepositoryProtocol
from claude_review.services.exit_report import exit_report
from claude_review.services.image_service import ImageService
from claude_review.services.review.agent_inbox import AgentInbox, Silence
from claude_review.services.review.answerer import Answerer
from claude_review.services.review.browser_presence import BrowserPresence
from claude_review.services.review.content_sources import ContentSource, Retaken, content_source
from claude_review.services.review.conversation import Conversation
from claude_review.services.review.reader_threads import ReaderThreads
from claude_review.services.review.review_content import ReviewContent
from claude_review.services.review.review_lifetime import EndReason, ReviewLifetime
from claude_review.services.review.round_tracker import RoundTracker
from claude_review.services.review.thread_handover import ThreadHandover
from claude_review.services.review_opening import ReviewOpening
from claude_review.services.review_service import ReviewService
from claude_review.services.transcript_review_service import TranscriptReviewService

log = structlog.get_logger()


class Review:
    """One review: its content, its rounds, its conversation, and the two sides it passes between."""

    def __init__(
        self,
        opening: ReviewOpening,
        *,
        repository: RepositoryProtocol,
        images: ImageService,
        page: PageChannel,
        presence: BrowserPresence,
        lifetime: ReviewLifetime,
        clock: Clock,
    ) -> None:
        self._mode = opening.mode
        self._title = opening.title
        self._page = page
        self._images = images
        self._presence = presence
        self._lifetime = lifetime
        self._rounds = RoundTracker()
        self._answerer = Answerer(page, clock)
        self._inbox = AgentInbox(lifetime)
        self._conversation = Conversation(clock)
        self._threads = ReaderThreads()
        self._handover = ThreadHandover(images)
        self._source: ContentSource = content_source(
            opening, repository=repository, clock=clock, rounds=self._rounds, page=page
        )
        # Chosen once: a review of a conversation quotes what each comment is
        # on, since the agent will not have the conversation in front of it
        self._formatter = (
            TranscriptReviewService(opening.diff_files) if opening.mode == ReviewMode.TRANSCRIPT else ReviewService()
        )

    @property
    def mode(self) -> ReviewMode:
        return self._mode

    @property
    def title(self) -> str:
        """What the header says is under review."""
        return self._title

    @property
    def lifetime(self) -> ReviewLifetime:
        return self._lifetime

    @property
    def presence(self) -> BrowserPresence:
        return self._presence

    @property
    def images(self) -> ImageService:
        return self._images

    @property
    def answerer(self) -> Answerer:
        return self._answerer

    @property
    def rounds(self) -> RoundTracker:
        return self._rounds

    @property
    def conversation(self) -> Conversation:
        return self._conversation

    @property
    def threads(self) -> ReaderThreads:
        return self._threads

    @property
    def source(self) -> ContentSource:
        return self._source

    @property
    def content(self) -> ReviewContent:
        """The take of the content on screen now."""
        return self._source.content

    async def open(self) -> None:
        """Note what the review opens on, before any page or agent can reach it."""
        await self._source.open()

    def news_for_a_new_page(self) -> list[PageEvent]:
        """What a page opening now must be told that nothing will tell it again: the work under way."""
        work = self._answerer.work
        return [WorkReported(work=work)] if work is not None else []

    async def next_event(self, *, within: float, caller_left: Awaitable[None]) -> AgentEvent | Silence:
        """The next thing the reader handed over, for the agent asking.

        Asking at all is what says an agent is there, which is what makes
        rounds worth offering in the review.
        """
        self._answerer.heard()
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
        log.info("thread_question", thread_id=thread.thread_id, where=handed.where)

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
        quoted = self.content.anchors.quote(anchor)
        thread_id = self._threads.raise_id()
        self._page.tell(ThreadRaised(thread_id=thread_id, anchor=quoted, body=body, severity=severity))
        log.info("thread_raised", thread_id=thread_id, where=quoted.where())
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
        result = self._formatter.format_review(
            [self._handover.thread(thread) for thread in threads], body, round_number=number
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
        self._page.tell(DiffRetaken(changes=retaken.changes))
        return retaken

    def end(self) -> None:
        """End a review that was kept open for rounds."""
        self._lifetime.end(EndReason.FINISHED)

    async def end_once_its_page_is_closed(self) -> None:
        """End the review once its page is closed rather than reloaded: for everyone, an agent waiting included."""
        if await self._lifetime.before_the_end(self._presence.until_closed_for_good()):
            self._lifetime.end(EndReason.BROWSER_CLOSED)

    async def tell_when_the_tree_moves(self) -> None:
        """Watch the tree under the review once a page is there to be told, until the review ends."""
        if await self._lifetime.before_the_end(self._presence.until_first_page()):
            await self._source.tell_when_the_tree_moves(self._lifetime)

    def exit_report(self) -> str:
        """What the review hands back as it ends: its rounds, and whatever the agent never took."""
        return exit_report(self._rounds.last_sent, self._inbox.drain())
