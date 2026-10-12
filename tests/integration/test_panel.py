"""The agent panel: talking about the review, not about one line.

A thread hangs on a line. The panel is for everything else — the plan, the
tests, a file nobody commented on — and it reaches the same agent, over the
same queue, so an answer written after a round arrives after it.
"""

from http import HTTPStatus

from fastapi.testclient import TestClient
from httpx import AsyncClient

from claude_review.domain.models import MAX_QUOTE_LINES, CommentSeverity, LineSide, TurnAuthor
from claude_review.presentation.wire.agent import ProgressStep
from claude_review.presentation.wire.pushes import ChatPush, PointPush, ProgressPush, ShowPush, StatusPush
from tests.helpers import (
    CATCH_UP_ROUTE,
    EVENTS_ROUTE,
    FIRST_THREAD_ID,
    REVIEW_ROUTE,
    REVIEWED_FILE,
    REVIEWED_LINE,
    WAIT_FOR_EVENT,
    FixedClock,
    ReviewFactory,
    http_client,
    line_on_the_wire,
    next_push,
    work_pushed,
    one_line_file,
    open_session,
    opening_of,
    page_client,
    pushes_until,
    review_facts,
    thread_on_the_wire,
    thread_route,
    turn_on_the_wire,
    until_the_review_holds_threads,
)

MESSAGE = {"message_id": "panel-1", "body": "Run the tests and say what fails."}

# A moment on the review's clock, in epoch milliseconds
A_MOMENT = 1_791_000_000_000
# A file the review does not hold
ELSEWHERE = "src/elsewhere.py"

THREAD = thread_on_the_wire(
    {**line_on_the_wire(REVIEWED_FILE, 42), "quote": ["    return now - self.started_at > timeout"]},
    "Why did you drop the None check?",
    turns=[turn_on_the_wire(TurnAuthor.AUTHOR, "It moved to the caller.", turn_id="turn-1")],
)

QUESTION = {"question_id": FIRST_THREAD_ID, "thread": THREAD}

POINT_ROUTE = "/api/point"


def _pointing(anchor: dict[str, object], body: str) -> dict[str, object]:
    """A thread the author raises, as its command sends it: an ordinary note."""
    return {"anchor": anchor, "body": body, "severity": CommentSeverity.NOTE}


async def test_a_message_reaches_whoever_is_waiting(client: AsyncClient) -> None:
    """What is typed in the panel is handed over as its own kind of event."""
    await client.post("/api/message", json=MESSAGE)

    event = (await client.post(EVENTS_ROUTE, params=WAIT_FOR_EVENT)).json()

    assert event["type"] == "message"
    assert event["message"]["body"] == "Run the tests and say what fails."
    assert event["message"]["message_id"] == "panel-1"


async def test_a_message_carries_the_threads_it_points_at(client: AsyncClient) -> None:
    """A chip is a reference; what travels is the thread it refers to."""
    await client.post("/api/message", json={**MESSAGE, "threads": [THREAD]})

    event = (await client.post(EVENTS_ROUTE, params=WAIT_FOR_EVENT)).json()

    [thread] = event["message"]["threads"]
    assert thread["thread_id"] == "comment-1"
    assert thread["anchor"]["quote"] == ["    return now - self.started_at > timeout"]
    assert thread["turns"][0]["body"] == "It moved to the caller."


async def test_a_message_pointing_at_a_thread_quoting_fewer_lines_than_it_names_is_refused(
    client: AsyncClient,
) -> None:
    """Handed over, the agent would take the quote for every line the thread names."""
    short = {**THREAD, "anchor": {**line_on_the_wire(REVIEWED_FILE, 40, 42), "quote": ["only line 40"]}}

    response = await client.post("/api/message", json={**MESSAGE, "threads": [short]})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert "names 3 lines but quotes 1" in response.json()["detail"]


async def test_questions_rounds_and_messages_keep_one_order(client: AsyncClient) -> None:
    """One queue, so an answer cannot overtake the round it belongs to."""
    await client.post("/api/ask", json=QUESTION)
    await client.post("/api/submit", json={"threads": [], "end": False})
    await client.post("/api/message", json=MESSAGE)

    handed_in_order = ["question", "round", "message"]

    taken = [(await client.post(EVENTS_ROUTE, params=WAIT_FOR_EVENT)).json()["type"] for _ in handed_in_order]

    assert taken == handed_in_order


def test_an_answer_lands_in_the_panel_of_a_review_still_open(review_page: TestClient) -> None:
    """The answer comes back down the socket every review already holds."""
    with open_session(review_page) as socket:
        review_page.post("/api/say", json={"message_id": "panel-1", "body": "One failed; fixed and green."})

        assert next_push(socket, ChatPush) == ChatPush(
            message_id="panel-1", body="One failed; fixed and green.", files=[]
        )


async def test_stopping_is_a_request_the_agent_picks_up(client: AsyncClient) -> None:
    """Nothing is killed: the withdrawal joins the queue like anything else."""
    await client.post("/api/message", json=MESSAGE)
    await client.post("/api/cancel", json={"message_id": "panel-1"})

    first = (await client.post(EVENTS_ROUTE, params=WAIT_FOR_EVENT)).json()
    second = (await client.post(EVENTS_ROUTE, params=WAIT_FOR_EVENT)).json()

    assert first["type"] == "message"
    assert second["type"] == "cancel"
    assert second["cancel"]["message_id"] == "panel-1"


def test_the_author_can_raise_a_thread_on_a_line(review_page: TestClient) -> None:
    """What belongs on the code goes on the code, not into the panel."""
    with open_session(review_page) as socket:
        response = review_page.post(
            POINT_ROUTE,
            json={
                "anchor": line_on_the_wire(REVIEWED_FILE, 1),
                "body": "I did this differently from what was asked, because...",
                "severity": CommentSeverity.QUESTION,
            },
        )
        pushed = next_push(socket, PointPush)

    assert response.json()["thread_id"] == "raised-1"
    assert pushed.thread_id == "raised-1"
    assert (pushed.anchor.file, pushed.anchor.start_line) == (REVIEWED_FILE, 1)
    # Quoted from the diff, so the thread can follow its line when it moves
    assert pushed.anchor.quote == [REVIEWED_LINE]
    assert pushed.severity == CommentSeverity.QUESTION


async def test_a_thread_the_agent_raised_can_be_answered_in(client: AsyncClient) -> None:
    """The reader may ask about it like any other, and the review knows it before the page says it holds it."""
    raised = await client.post(POINT_ROUTE, json=_pointing(line_on_the_wire(REVIEWED_FILE, 1), "Kept on purpose"))

    response = await client.post("/api/reply", json={"thread_id": raised.json()["thread_id"], "body": "Because"})

    assert response.status_code == HTTPStatus.NO_CONTENT


async def test_raised_threads_are_numbered_apart_from_the_readers(client: AsyncClient) -> None:
    """The browser mints its own ids; two sides must not collide."""
    first = await client.post(POINT_ROUTE, json=_pointing(line_on_the_wire(REVIEWED_FILE, 1), "one"))
    second = await client.post(POINT_ROUTE, json=_pointing(line_on_the_wire(REVIEWED_FILE, 1), "two"))

    assert first.json()["thread_id"] == "raised-1"
    assert second.json()["thread_id"] == "raised-2"


async def test_a_backwards_range_is_refused(client: AsyncClient) -> None:
    """A thread that ends before it starts hangs on nothing."""
    response = await client.post(POINT_ROUTE, json=_pointing(line_on_the_wire(REVIEWED_FILE, 9, 2), "nowhere"))

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT


async def test_a_thread_on_a_file_not_under_review_is_refused(client: AsyncClient) -> None:
    """Silently accepting it shows the reader a thread about nothing."""
    response = await client.post(POINT_ROUTE, json=_pointing(line_on_the_wire("src/elsewhere.py", 1), "here"))

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "not in this review" in response.json()["detail"]
    assert REVIEWED_FILE in response.json()["detail"]


async def test_a_thread_on_the_removed_side_must_hang_on_a_removed_line(client: AsyncClient) -> None:
    """An unchanged line has an old number too, but nothing was removed there to talk about."""
    response = await client.post(
        POINT_ROUTE, json=_pointing(line_on_the_wire(REVIEWED_FILE, 1, side=LineSide.OLD), "this one")
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert "does not show removed line 1" in response.json()["detail"]


async def test_a_thread_on_a_line_the_diff_does_not_show_is_refused(client: AsyncClient) -> None:
    """The quote would come back empty and go outdated at the next retake."""
    response = await client.post(POINT_ROUTE, json=_pointing(line_on_the_wire(REVIEWED_FILE, 900), "far away"))

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert "does not show new line 900" in response.json()["detail"]


async def test_a_thread_on_more_lines_than_a_round_can_carry_is_refused(client: AsyncClient) -> None:
    """Raised, it would block every round until the reader found it and deleted it."""
    too_many = line_on_the_wire(REVIEWED_FILE, 1, MAX_QUOTE_LINES + 1)

    response = await client.post(POINT_ROUTE, json=_pointing(too_many, "all of it"))

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert str(MAX_QUOTE_LINES) in response.json()["detail"]


async def test_a_thread_on_a_line_the_diff_does_show_is_taken(client: AsyncClient) -> None:
    """The check is a guard, not a hurdle: what is on screen goes through."""
    response = await client.post(POINT_ROUTE, json=_pointing(line_on_the_wire(REVIEWED_FILE, 1), "this line"))

    assert response.status_code == HTTPStatus.OK


def test_the_agent_may_speak_first(review_page: TestClient) -> None:
    """Work finished while the reader reads is news they should not have to ask for."""
    with open_session(review_page) as socket:
        review_page.post("/api/say", json={"body": "Tests are green again.", "files": [REVIEWED_FILE]})
        pushed = next_push(socket, ChatPush)

    assert pushed.message_id is None
    assert pushed.files == [REVIEWED_FILE]


async def test_words_naming_a_file_the_review_does_not_hold_are_refused_and_nothing_is_said(
    client: AsyncClient,
) -> None:
    """A chip to a file the review does not hold would take the reader nowhere, while the agent took it as said."""
    response = await client.post("/api/say", json={"body": "Renamed both.", "files": [REVIEWED_FILE, ELSEWHERE]})

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert f"{ELSEWHERE} is not in this review" in response.json()["detail"]
    assert (await client.get(CATCH_UP_ROUTE)).json()["panel"] == []


async def test_work_naming_a_file_the_review_does_not_hold_is_refused_and_nothing_is_shown(
    client: AsyncClient,
) -> None:
    """The same chip, on the line that says what is being done."""
    response = await client.post("/api/progress", json={"text": "renaming", "files": [ELSEWHERE]})

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert f"{ELSEWHERE} is not in this review" in response.json()["detail"]
    assert (await client.get(REVIEW_ROUTE)).json()["work"] is None


def test_what_is_being_done_is_said_while_it_is_done(review_page: TestClient) -> None:
    """Waiting says only that something is happening; this says what."""
    with open_session(review_page) as socket:
        review_page.post(
            "/api/progress",
            json={"message_id": "panel-1", "text": "rewriting the answer handler", "files": [REVIEWED_FILE]},
        )
        work = work_pushed(socket)

    assert work.text == "rewriting the answer handler"
    assert work.files == [REVIEWED_FILE]
    assert work.message_id == "panel-1"


def test_work_that_branched_is_reported_as_branches(review_page: TestClient) -> None:
    """Three subagents are three branches, not a sentence about three subagents."""
    with open_session(review_page) as socket:
        review_page.post(
            "/api/progress",
            json={
                "text": "looking for other callers",
                "steps": [{"text": "ran the tests", "done": True}, {"text": "three subagents out"}],
            },
        )
        work = work_pushed(socket)

    assert work.steps == [
        ProgressStep(text="ran the tests", done=True),
        ProgressStep(text="three subagents out", done=False),
    ]


def test_work_is_dated_when_it_was_reported(reviews: ReviewFactory) -> None:
    """A review reloaded later says how long the work has gone on, not that it just began."""
    with (
        page_client(reviews.app(opening_of([one_line_file()]), clock=FixedClock(A_MOMENT))) as review_page,
        open_session(review_page) as socket,
    ):
        review_page.post("/api/progress", json={"text": "reading the handler"})
        work = work_pushed(socket)

    assert work.at == A_MOMENT


def test_a_review_opened_while_work_is_under_way_is_told_what_is_being_done(review_page: TestClient) -> None:
    """A push is gone once sent, and a reload must not lose the line saying what the agent is doing."""
    review_page.post("/api/progress", json={"text": "rewriting the answer handler", "files": [REVIEWED_FILE]})

    work = review_facts(review_page).work

    assert work is not None
    assert work.text == "rewriting the answer handler"
    assert work.files == [REVIEWED_FILE]


def test_an_empty_report_says_the_work_is_over(review_page: TestClient) -> None:
    with open_session(review_page) as socket:
        review_page.post("/api/progress", json={"text": "reading the handler"})
        next_push(socket, ProgressPush)
        review_page.post("/api/progress", json={"text": ""})

        assert next_push(socket, ProgressPush) == ProgressPush(work=None)


def test_the_answer_ends_the_work_it_answers(review_page: TestClient) -> None:
    """Said to every review on screen, so no tab goes on showing it."""
    with open_session(review_page) as socket:
        review_page.post("/api/progress", json={"message_id": "panel-1", "text": "reading the handler"})
        next_push(socket, ProgressPush)
        review_page.post("/api/say", json={"message_id": "panel-1", "body": "It retries twice."})

        assert next_push(socket, ProgressPush) == ProgressPush(work=None)


def test_an_answer_to_another_message_leaves_the_work_showing(review_page: TestClient) -> None:
    """Work of the agent's own — reviewers reading, a round worked through — outlives any answer."""
    with open_session(review_page) as socket:
        review_page.post("/api/progress", json={"text": "four reviewers reading"})
        review_page.post("/api/say", json={"message_id": "panel-1", "body": "Two fail."})
        review_page.post("/api/show", json={"file": REVIEWED_FILE})
        pushed = pushes_until(socket, ShowPush)

    assert sum(isinstance(push, ProgressPush) for push in pushed) == 1


def test_a_new_message_ends_the_work_shown_for_the_last_one(review_page: TestClient) -> None:
    """A new question, so whatever was being done for the last one is history."""
    with open_session(review_page) as socket:
        review_page.post("/api/progress", json={"message_id": "panel-1", "text": "reading the handler"})
        next_push(socket, ProgressPush)
        review_page.post("/api/message", json={**MESSAGE, "message_id": "panel-2"})

        assert next_push(socket, ProgressPush) == ProgressPush(work=None)


def test_a_message_that_is_refused_leaves_the_work_showing(review_page: TestClient) -> None:
    """Nothing new was asked, so whatever was being done is still being done."""
    review_page.post("/api/progress", json={"text": "reading the handler"})
    refused = review_page.post("/api/message", json={**MESSAGE, "images": ["never-kept.png"]})

    work = review_facts(review_page).work

    assert refused.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert work is not None
    assert work.text == "reading the handler"


def test_taking_a_message_back_ends_the_work_for_it(review_page: TestClient) -> None:
    """The reader pressed Stop; the line must not go on saying the agent works on it."""
    with open_session(review_page) as socket:
        review_page.post("/api/progress", json={"message_id": "panel-1", "text": "reading the handler"})
        next_push(socket, ProgressPush)
        review_page.post("/api/cancel", json={"message_id": "panel-1"})

        assert next_push(socket, ProgressPush) == ProgressPush(work=None)


def test_work_that_is_over_is_not_shown_to_a_review_opened_after(review_page: TestClient) -> None:
    """The answer ended it; a reload must not bring the line back."""
    review_page.post("/api/progress", json={"message_id": "panel-1", "text": "reading the handler"})
    review_page.post("/api/say", json={"message_id": "panel-1", "body": "It retries twice."})

    assert review_facts(review_page).work is None


def test_a_file_can_be_brought_into_view_when_asked(review_page: TestClient) -> None:
    """The one thing here that moves the reader's own screen."""
    with open_session(review_page) as socket:
        review_page.post("/api/show", json={"file": REVIEWED_FILE})

        assert next_push(socket, ShowPush) == ShowPush(file=REVIEWED_FILE)


async def test_a_file_not_in_the_review_is_not_shown(client: AsyncClient) -> None:
    """The page would go nowhere, and the agent would believe the reader had been taken there."""
    response = await client.post("/api/show", json={"file": "src/elsewhere.py"})

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "src/elsewhere.py" in response.json()["detail"]


def test_the_agent_says_what_only_the_agent_knows(review_page: TestClient) -> None:
    """Model and context cannot be measured here, so they are reported."""
    with open_session(review_page) as socket:
        review_page.post("/api/status", json={"model": "opus-5", "context": "53% of 1M"})
        pushed = next_push(socket, StatusPush)

    assert (pushed.agent.model, pushed.agent.context) == ("opus-5", "53% of 1M")


async def test_a_reloaded_review_learns_the_status_again(client: AsyncClient) -> None:
    """A push is gone once sent; the review has to get it from somewhere."""
    await client.post("/api/status", json={"model": "opus-5", "context": "53% of 1M"})

    standing = (await client.get(REVIEW_ROUTE)).json()

    assert standing["agent"]["model"] == "opus-5"
    assert standing["agent"]["context"] == "53% of 1M"
    assert standing["agent"]["at"] is not None


async def test_a_status_is_dated_when_it_was_reported(reviews: ReviewFactory) -> None:
    """The panel says how old the numbers are, so the date is the review's own clock."""
    async with http_client(reviews.app(opening_of([one_line_file()]), clock=FixedClock(A_MOMENT))) as client:
        await client.post("/api/status", json={"model": "opus-5"})
        standing = (await client.get(REVIEW_ROUTE)).json()

    assert standing["agent"]["at"] == A_MOMENT


async def test_what_is_said_in_the_panel_is_dated_when_it_was_said(reviews: ReviewFactory) -> None:
    async with http_client(reviews.app(opening_of([one_line_file()]), clock=FixedClock(A_MOMENT))) as client:
        await client.post("/api/message", json=MESSAGE)
        await client.post("/api/say", json={"message_id": MESSAGE["message_id"], "body": "Two fail."})
        panel = (await client.get(CATCH_UP_ROUTE)).json()["panel"]

    assert [entry["at"] for entry in panel] == [A_MOMENT, A_MOMENT]


async def test_no_status_is_reported_as_nothing_rather_than_zero(client: AsyncClient) -> None:
    """A number nobody sent is a lie; the panel shows it as unknown."""
    standing = (await client.get(REVIEW_ROUTE)).json()

    assert standing["agent"] == {"model": None, "context": None, "at": None}


A_DISCUSSED_THREAD = thread_on_the_wire(
    {**line_on_the_wire(REVIEWED_FILE, 1), "quote": [REVIEWED_LINE]},
    "Why did you drop the None check?",
    severity=CommentSeverity.QUESTION,
    turns=[turn_on_the_wire(TurnAuthor.AUTHOR, "It moved to the caller.", turn_id="turn-1")],
)


def test_an_agent_arriving_late_is_told_what_the_review_holds(review_page: TestClient) -> None:
    """`events` hands over what happens next, never what already happened."""
    with open_session(review_page) as socket:
        socket.send_json({"threads": [A_DISCUSSED_THREAD]})
        until_the_review_holds_threads(review_page, 1)
    review_page.post("/api/message", json=MESSAGE)
    review_page.post("/api/say", json={"message_id": "panel-1", "body": "One failed; fixed."})

    seen = review_page.get(CATCH_UP_ROUTE).json()

    assert seen["round"] == 1
    assert seen["file_count"] == 1
    assert [(thread["thread_id"], thread["turn_count"]) for thread in seen["threads"]] == [("comment-1", 1)]
    assert [(entry["author"], entry["body"]) for entry in seen["panel"]] == [
        ("reader", "Run the tests and say what fails."),
        ("author", "One failed; fixed."),
    ]


def test_one_thread_can_be_asked_for_on_its_own(review_page: TestClient) -> None:
    """An index is for choosing what to read; this is the reading."""
    with open_session(review_page) as socket:
        socket.send_json({"threads": [A_DISCUSSED_THREAD, {**A_DISCUSSED_THREAD, "thread_id": "comment-2"}]})
        until_the_review_holds_threads(review_page, 2)

    read = review_page.post(thread_route("comment-2")).json()

    assert read["thread_id"] == "comment-2"
    assert [turn["body"] for turn in read["turns"]] == ["It moved to the caller."]
    assert read["anchor"]["quote"] == [REVIEWED_LINE]
