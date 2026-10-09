"""Handing a thread from the reader's page to the agent: its screenshots become files the agent may open."""

from pathlib import Path

import structlog

from claude_review.domain.models import Thread, ThreadDraft, Turn, TurnDraft
from claude_review.services.image_service import ImageService

log = structlog.get_logger()


class ThreadHandover:
    """Turns the threads a page holds into threads an agent reads.

    Every image a thread names is handed over on the way: kept until the
    review ends, since the agent may open it at any time from then on, and no
    longer the reader's to take off.
    """

    def __init__(self, images: ImageService) -> None:
        self._images = images

    def thread(self, thread: ThreadDraft) -> Thread:
        """A thread as the agent is handed it, turns and all."""
        return Thread(
            thread_id=thread.thread_id,
            anchor=thread.anchor,
            severity=thread.severity,
            body=thread.body,
            images=self.kept_images(thread.images),
            turns=[self._turn(turn) for turn in thread.turns],
            raised_by=thread.raised_by,
            resolved=thread.resolved,
        )

    def kept_images(self, image_ids: list[str]) -> list[Path]:
        """Hand over the images this review still keeps.

        A thread outlives a restart of the server in the reader's draft, and the
        screenshots in it do not: one that is gone drops out, rather than holding
        up the question or the round it travels in — but not without a trace.
        """
        handover = self._images.hand_over(image_ids)
        if handover.missing:
            log.info("images_dropped", missing=handover.missing)
        return handover.paths

    def _turn(self, turn: TurnDraft) -> Turn:
        return Turn(author=turn.author, body=turn.body, round=turn.round, images=self.kept_images(turn.images))
