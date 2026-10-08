"""Asking about a thread, and the answer coming back.

The reader asks from the browser and carries on writing; the answer arrives
later, pushed into the review that is still on screen. The two halves are
separate processes, which is why a queue sits between them.
"""

from http import HTTPStatus

from fastapi.testclient import TestClient
from httpx import AsyncClient

from claude_review.domain.models import CommentSeverity, TurnAuthor
from tests.helpers import (
    EVENTS_ROUTE,
    FIRST_THREAD_ID,
    LOCAL_HEADERS,
    WAIT_FOR_EVENT,
    line_on_the_wire,
    next_push,
    open_session,
    review_has_ended,
    thread_on_the_wire,
    turn_on_the_wire,
)

ASK_ROUTE = "/api/ask"

OPENING = "Why did you drop the None check?"
QUOTED = "    return now - self.started_at > timeout"
ANCHOR = {**line_on_the_wire("src/a.py", 42), "quote": [QUOTED]}

# A thread nothing was said in since the comment that opened it
A_THREAD = thread_on_the_wire(ANCHOR, OPENING)
# What the agent answered, and what the reader asked next
ANSWER = turn_on_the_wire(TurnAuthor.AUTHOR, "It moved to the caller.")
FOLLOW_UP = turn_on_the_wire(TurnAuthor.READER, "Which caller?")
# An image id the review never kept, or no longer keeps after a restart
GONE_IMAGE = "gone.png"


def _asking(thread: dict[str, object], question_id: str = FIRST_THREAD_ID) -> dict[str, object]:
    """A question as the page sends it: which one, and the whole thread it is asked in."""
    return {"question_id": question_id, "thread": thread}


async def _question_taken(client: AsyncClient) -> dict:
    """The question as the agent is handed it."""
    return (await client.get(EVENTS_ROUTE, params=WAIT_FOR_EVENT)).json()["question"]


async def test_a_question_waits_for_whoever_is_answering(client: AsyncClient) -> None:
    """Asking does not block the reader; it leaves the question for whoever comes to take it."""
    response = await client.post(ASK_ROUTE, json=_asking(A_THREAD))
    taken_later = await _question_taken(client)

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert taken_later["thread"]["thread_id"] == FIRST_THREAD_ID


async def test_the_answerer_is_handed_the_question_in_its_thread(client: AsyncClient) -> None:
    await client.post(ASK_ROUTE, json=_asking(A_THREAD))

    event = (await client.get(EVENTS_ROUTE, params=WAIT_FOR_EVENT)).json()

    assert event["type"] == "question"
    assert event["question"]["body"] == OPENING
    # The quoted lines travel with it, since the answerer may not have the file
    assert event["question"]["thread"]["anchor"]["quote"] == [QUOTED]
    assert event["question"]["thread"]["where"] == "`src/a.py`:42"


async def test_a_thread_nothing_was_said_in_asks_the_comment_that_opened_it(client: AsyncClient) -> None:
    await client.post(ASK_ROUTE, json=_asking(A_THREAD))

    question = await _question_taken(client)

    assert (question["body"], question["thread"]["turns"]) == (OPENING, [])


async def test_asking_after_the_readers_own_reply_asks_that_reply(client: AsyncClient) -> None:
    """The reply just written is what the reader wants answered, not the comment it follows."""
    await client.post(ASK_ROUTE, json=_asking({**A_THREAD, "turns": [ANSWER, FOLLOW_UP]}, question_id="turn-2"))

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


async def test_an_opening_asked_with_an_image_the_review_does_not_keep_is_refused(client: AsyncClient) -> None:
    """Pasted a moment ago, so a missing one is a fault, not a screenshot lost to a restart."""
    response = await client.post(ASK_ROUTE, json=_asking({**A_THREAD, "images": [GONE_IMAGE]}))

    assert response.status_code == 422


async def test_a_reply_asked_with_an_image_the_review_does_not_keep_is_refused(client: AsyncClient) -> None:
    asked = {**FOLLOW_UP, "images": [GONE_IMAGE]}

    response = await client.post(ASK_ROUTE, json=_asking({**A_THREAD, "turns": [ANSWER, asked]}))

    assert response.status_code == 422


async def test_an_image_earlier_in_the_thread_that_did_not_survive_a_restart_is_left_out(
    client: AsyncClient,
) -> None:
    """Only what is asked was pasted a moment ago; the rest may predate a restart."""
    earlier = {**A_THREAD, "images": [GONE_IMAGE], "turns": [ANSWER, FOLLOW_UP]}

    response = await client.post(ASK_ROUTE, json=_asking(earlier))
    question = await _question_taken(client)

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert question["thread"]["images"] == []


async def test_questions_are_handed_out_in_the_order_they_were_asked(
    client: AsyncClient,
) -> None:
    await client.post(ASK_ROUTE, json=_asking({**A_THREAD, "thread_id": "first", "body": "one"}))
    await client.post(ASK_ROUTE, json=_asking({**A_THREAD, "thread_id": "second", "body": "two"}))

    first = await _question_taken(client)
    second = await _question_taken(client)

    assert [first["thread"]["thread_id"], second["thread"]["thread_id"]] == ["first", "second"]


async def test_a_question_needs_something_asked(client: AsyncClient) -> None:
    response = await client.post(ASK_ROUTE, json=_asking({**A_THREAD, "body": ""}))

    assert response.status_code == 422


async def test_a_question_carries_which_question_it_is(client: AsyncClient) -> None:
    """A thread can have several questions waiting, so an answer needs a name for one."""
    await client.post(ASK_ROUTE, json=_asking(A_THREAD, question_id="turn-2"), headers=LOCAL_HEADERS)

    event = (await client.get(EVENTS_ROUTE, params=WAIT_FOR_EVENT, headers=LOCAL_HEADERS)).json()

    assert event["question"]["question_id"] == "turn-2"


def test_an_answer_says_which_question_it_answers(review_page: TestClient) -> None:
    """Without it the browser files the answer under whatever was asked last."""
    with open_session(review_page) as socket:
        review_page.post(
            "/api/reply",
            json={"thread_id": "comment-1", "question_id": "turn-2", "text": "It moved to config"},
        )

        assert next_push(socket, "reply") == {
            "type": "reply",
            "thread_id": "comment-1",
            "question_id": "turn-2",
            "text": "It moved to config",
        }


def test_an_answer_that_names_no_question_still_arrives(review_page: TestClient) -> None:
    """A person answering by hand should not have to quote an id."""
    with open_session(review_page) as socket:
        review_page.post("/api/reply", json={"thread_id": "comment-1", "text": "It moved to config"})

        assert next_push(socket, "reply") == {
            "type": "reply",
            "thread_id": "comment-1",
            "question_id": None,
            "text": "It moved to config",
        }


async def test_waiting_after_the_review_ended_says_so_at_once(client: AsyncClient) -> None:
    await client.post("/api/end")

    assert await review_has_ended(client)
