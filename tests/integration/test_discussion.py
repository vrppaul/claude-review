"""Asking about a thread, and the answer coming back.

The reader asks from the browser and carries on writing; the answer arrives
later, pushed into the review that is still on screen. The two halves are
separate processes, which is why a queue sits between them.
"""

from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from claude_review.domain.models import CommentSeverity, TurnAuthor
from claude_review.presentation.wire.pushes import ReplyPush
from tests.helpers import (
    EVENTS_ROUTE,
    FIRST_THREAD_ID,
    LOCAL_HEADERS,
    REVIEWED_FILE,
    REVIEWED_LINE,
    WAIT_FOR_EVENT,
    line_on_the_wire,
    next_push,
    open_session,
    review_has_ended,
    thread_on_the_wire,
    turn_on_the_wire,
    until_the_review_holds_threads,
)

ASK_ROUTE = "/api/ask"

OPENING = "Why did you drop the None check?"
QUOTED = "    return now - self.started_at > timeout"
ANCHOR = {**line_on_the_wire("src/a.py", 42), "quote": [QUOTED]}

# A thread nothing was said in since the comment that opened it
A_THREAD = thread_on_the_wire(ANCHOR, OPENING)
# What the agent answered, and what the reader asked next
ANSWER_ID = "turn-1"
FOLLOW_UP_ID = "turn-2"
ANSWER = turn_on_the_wire(TurnAuthor.AUTHOR, "It moved to the caller.", turn_id=ANSWER_ID)
FOLLOW_UP = turn_on_the_wire(TurnAuthor.READER, "Which caller?", turn_id=FOLLOW_UP_ID)
# An image id the review never kept, or no longer keeps after a restart
GONE_IMAGE = "gone.png"
# What the agent opens a thread of its own with
RAISED_BODY = "I kept the old name; renaming it broke two callers."


def _asking(thread: dict[str, object], question_id: str = FIRST_THREAD_ID) -> dict[str, object]:
    """A question as the page sends it: which one, and the whole thread it is asked in."""
    return {"question_id": question_id, "thread": thread}


async def _question_taken(client: AsyncClient) -> dict:
    """The question as the agent is handed it."""
    return (await client.post(EVENTS_ROUTE, params=WAIT_FOR_EVENT)).json()["question"]


async def test_a_question_waits_for_whoever_is_answering(client: AsyncClient) -> None:
    """Asking does not block the reader; it leaves the question for whoever comes to take it."""
    response = await client.post(ASK_ROUTE, json=_asking(A_THREAD))
    taken_later = await _question_taken(client)

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert taken_later["thread"]["thread_id"] == FIRST_THREAD_ID


async def test_the_answerer_is_handed_the_question_in_its_thread(client: AsyncClient) -> None:
    await client.post(ASK_ROUTE, json=_asking(A_THREAD))

    event = (await client.post(EVENTS_ROUTE, params=WAIT_FOR_EVENT)).json()

    assert event["type"] == "question"
    assert event["question"]["body"] == OPENING
    # The quoted lines travel with it, since the answerer may not have the file
    assert event["question"]["thread"]["anchor"]["quote"] == [QUOTED]
    assert event["question"]["thread"]["where"] == "src/a.py:42"


async def test_a_thread_nothing_was_said_in_asks_the_comment_that_opened_it(client: AsyncClient) -> None:
    await client.post(ASK_ROUTE, json=_asking(A_THREAD))

    question = await _question_taken(client)

    assert (question["body"], question["thread"]["turns"]) == (OPENING, [])


async def test_asking_after_the_readers_own_reply_asks_that_reply(client: AsyncClient) -> None:
    """The reply just written is what the reader wants answered, not the comment it follows."""
    await client.post(ASK_ROUTE, json=_asking({**A_THREAD, "turns": [ANSWER, FOLLOW_UP]}, question_id=FOLLOW_UP_ID))

    question = await _question_taken(client)

    assert question["body"] == "Which caller?"
    # Asked in the thread, not apart from it: what led up to it goes along
    assert [turn["body"] for turn in question["thread"]["turns"]] == ["It moved to the caller.", "Which caller?"]


async def test_asking_a_thread_the_agent_spoke_last_in_asks_the_comment_that_opened_it(client: AsyncClient) -> None:
    """With nothing new from the reader, asking again is asking about the thread itself."""
    await client.post(ASK_ROUTE, json=_asking({**A_THREAD, "turns": [FOLLOW_UP, ANSWER]}))

    question = await _question_taken(client)

    assert question["body"] == OPENING


async def test_a_question_says_how_its_thread_is_meant_to_be_taken(client: AsyncClient) -> None:
    """A blocker and a settled note are different instructions, whichever turn is asked about."""
    taken = {**A_THREAD, "severity": CommentSeverity.BLOCKER, "resolved": True, "raised_by": TurnAuthor.AUTHOR}
    await client.post(ASK_ROUTE, json=_asking(taken))

    thread = (await _question_taken(client))["thread"]

    assert (thread["severity"], thread["resolved"], thread["raised_by"]) == ("blocker", True, "author")


async def test_an_opening_asked_with_an_image_the_review_no_longer_keeps_is_asked_without_it(
    client: AsyncClient,
) -> None:
    """After a restart a screenshot is gone, whenever it was pasted; the question still goes."""
    response = await client.post(ASK_ROUTE, json=_asking({**A_THREAD, "images": [GONE_IMAGE]}))
    question = await _question_taken(client)

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert (question["body"], question["images"]) == (OPENING, [])


async def test_a_reply_asked_again_after_a_restart_is_asked_without_what_the_restart_lost(
    client: AsyncClient,
) -> None:
    """The reader's own last word, asked again: its screenshot may predate the restart."""
    asked = {**FOLLOW_UP, "images": [GONE_IMAGE]}

    response = await client.post(
        ASK_ROUTE, json=_asking({**A_THREAD, "turns": [ANSWER, asked]}, question_id=FOLLOW_UP_ID)
    )
    question = await _question_taken(client)

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert (question["body"], question["images"]) == ("Which caller?", [])


async def test_an_image_earlier_in_the_thread_that_did_not_survive_a_restart_is_left_out(
    client: AsyncClient,
) -> None:
    """Only what is asked was pasted a moment ago; the rest may predate a restart."""
    earlier = {**A_THREAD, "images": [GONE_IMAGE], "turns": [ANSWER, FOLLOW_UP]}

    response = await client.post(ASK_ROUTE, json=_asking(earlier, question_id=FOLLOW_UP_ID))
    question = await _question_taken(client)

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert question["thread"]["images"] == []


async def test_asking_again_after_a_restart_does_not_need_what_the_restart_lost(client: AsyncClient) -> None:
    """Asked again once the agent has answered, the opening is not fresh; its screenshot may be gone."""
    asked_again = {**A_THREAD, "images": [GONE_IMAGE], "turns": [FOLLOW_UP, ANSWER]}

    response = await client.post(ASK_ROUTE, json=_asking(asked_again))
    question = await _question_taken(client)

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert (question["body"], question["images"]) == (OPENING, [])


async def test_an_id_that_could_not_be_read_back_is_refused(client: AsyncClient) -> None:
    """A thread is read back at a path of its own, where a slash would name another route."""
    response = await client.post(ASK_ROUTE, json=_asking({**A_THREAD, "thread_id": "a/b"}, question_id="a/b"))

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT


async def test_a_question_in_a_thread_quoting_fewer_lines_than_it_names_is_refused(client: AsyncClient) -> None:
    """Handed over, the agent would take the quote for every line the thread names."""
    short = {**A_THREAD, "anchor": {**line_on_the_wire("src/a.py", 40, 42), "quote": [QUOTED]}}

    response = await client.post(ASK_ROUTE, json=_asking(short))

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert "names 3 lines but quotes 1" in response.json()["detail"]


async def test_a_question_naming_nothing_in_its_thread_is_refused(client: AsyncClient) -> None:
    response = await client.post(ASK_ROUTE, json=_asking({**A_THREAD, "turns": [ANSWER]}, question_id="turn-9"))

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT


async def test_a_question_cannot_ask_what_the_agent_said(client: AsyncClient) -> None:
    """A question is the reader's; naming the agent's own answer asks nothing."""
    response = await client.post(ASK_ROUTE, json=_asking({**A_THREAD, "turns": [ANSWER]}, question_id=ANSWER_ID))

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT


async def test_questions_are_handed_out_in_the_order_they_were_asked(
    client: AsyncClient,
) -> None:
    await client.post(ASK_ROUTE, json=_asking({**A_THREAD, "thread_id": "first", "body": "one"}, question_id="first"))
    await client.post(ASK_ROUTE, json=_asking({**A_THREAD, "thread_id": "second", "body": "two"}, question_id="second"))

    first = await _question_taken(client)
    second = await _question_taken(client)

    assert [first["thread"]["thread_id"], second["thread"]["thread_id"]] == ["first", "second"]


async def test_a_question_needs_something_asked(client: AsyncClient) -> None:
    response = await client.post(ASK_ROUTE, json=_asking({**A_THREAD, "body": ""}))

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT


async def test_a_question_carries_which_question_it_is(client: AsyncClient) -> None:
    """A thread can have several questions waiting, so an answer needs a name for one."""
    asked_in_a_reply = {**A_THREAD, "turns": [ANSWER, FOLLOW_UP]}
    await client.post(ASK_ROUTE, json=_asking(asked_in_a_reply, question_id=FOLLOW_UP_ID), headers=LOCAL_HEADERS)

    event = (await client.post(EVENTS_ROUTE, params=WAIT_FOR_EVENT, headers=LOCAL_HEADERS)).json()

    assert event["question"]["question_id"] == FOLLOW_UP_ID


def test_an_answer_says_which_question_it_answers(review_page: TestClient) -> None:
    """Without it the browser files the answer under the oldest question still waiting."""
    with open_session(review_page) as socket:
        socket.send_json({"threads": [A_THREAD]})
        until_the_review_holds_threads(review_page, 1)
        review_page.post(
            "/api/reply",
            json={"thread_id": "comment-1", "question_id": "turn-2", "body": "It moved to config"},
        )

        assert next_push(socket, ReplyPush) == ReplyPush(
            thread_id="comment-1", question_id="turn-2", body="It moved to config"
        )


def test_an_answer_that_names_no_question_still_arrives(review_page: TestClient) -> None:
    """A person answering by hand should not have to quote an id."""
    with open_session(review_page) as socket:
        socket.send_json({"threads": [A_THREAD]})
        until_the_review_holds_threads(review_page, 1)
        review_page.post("/api/reply", json={"thread_id": "comment-1", "body": "It moved to config"})

        assert next_push(socket, ReplyPush) == ReplyPush(
            thread_id="comment-1", question_id=None, body="It moved to config"
        )


async def test_an_answer_to_a_thread_the_review_never_heard_of_is_refused(client: AsyncClient) -> None:
    """The page would drop it, and the agent would never learn that its answer went nowhere."""
    response = await client.post("/api/reply", json={"thread_id": "comment-99", "body": "Because"})

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "comment-99" in response.json()["detail"]


async def test_a_thread_asked_about_can_be_answered_before_the_page_says_it_holds_it(client: AsyncClient) -> None:
    """A page says what it holds at most once a second, and a question is word enough that the thread is there."""
    await client.post(ASK_ROUTE, json=_asking(A_THREAD))

    response = await client.post("/api/reply", json={"thread_id": FIRST_THREAD_ID, "body": "Because"})

    assert response.status_code == HTTPStatus.NO_CONTENT


async def _raise_a_thread(client: AsyncClient) -> dict[str, object]:
    """The agent raises a thread on the reviewed line; the thread as the page then holds and sends it."""
    raised = await client.post(
        "/api/point",
        json={"anchor": line_on_the_wire(REVIEWED_FILE, 1), "body": RAISED_BODY, "severity": CommentSeverity.NOTE},
    )
    anchor = {**line_on_the_wire(REVIEWED_FILE, 1), "quote": [REVIEWED_LINE]}
    return thread_on_the_wire(anchor, RAISED_BODY, thread_id=raised.json()["thread_id"], raised_by=TurnAuthor.AUTHOR)


async def test_the_agents_own_thread_is_asked_about_as_it_raised_it(client: AsyncClient) -> None:
    raised = await _raise_a_thread(client)
    answered = {**raised, "turns": [turn_on_the_wire(TurnAuthor.READER, "Why keep it?", turn_id=FOLLOW_UP_ID)]}

    response = await client.post(ASK_ROUTE, json=_asking(answered, question_id=FOLLOW_UP_ID))

    assert response.status_code == HTTPStatus.NO_CONTENT


async def test_a_thread_the_agent_raised_is_refused_with_the_readers_words_in_its_opening(
    client: AsyncClient,
) -> None:
    """The agent would read the reader's words as its own: the opening of its thread is the agent's alone."""
    raised = await _raise_a_thread(client)
    rewritten = {**raised, "body": "Rename it after all."}

    response = await client.post(ASK_ROUTE, json=_asking(rewritten, question_id=str(raised["thread_id"])))

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert "only the agent" in response.json()["detail"]


@pytest.mark.parametrize(
    "changed",
    [
        {"severity": CommentSeverity.BLOCKER},
        {"images": [GONE_IMAGE]},
        {"raised_by": TurnAuthor.READER},
    ],
    ids=["reweighed", "with an image", "claimed by the reader"],
)
async def test_a_round_carrying_the_agents_thread_changed_is_refused(
    client: AsyncClient, changed: dict[str, object]
) -> None:
    raised = await _raise_a_thread(client)

    response = await client.post("/api/submit", json={"threads": [{**raised, **changed}], "end": False})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT


async def test_waiting_after_the_review_ended_says_so_at_once(client: AsyncClient) -> None:
    await client.post("/api/end")

    assert await review_has_ended(client)
