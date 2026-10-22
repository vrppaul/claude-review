"""The agent panel: talking about the review, not about one line.

A thread hangs on a line. The panel is for everything else — the plan, the
tests, a file nobody commented on — and it reaches the same agent, over the
same queue, so an answer written after a round arrives after it.
"""

from http import HTTPStatus
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from claude_review.domain.models import CommentSeverity, TurnAuthor
from claude_review.presentation.schemas.agent import ProgressStep
from claude_review.presentation.schemas.pushes import (
    ChatPush,
    HandedPush,
    PointPush,
    ProgressPush,
    ShowPush,
    StatusPush,
)
from tests.helpers import (
    CATCH_UP_ROUTE,
    CONVERSATION_ROUTE,
    EVENTS_ROUTE,
    FIRST_THREAD_ID,
    GLANCE_AT_EVENTS,
    PANEL_MESSAGE_ID,
    REVIEW_ROUTE,
    REVIEWED_FILE,
    REVIEWED_LINE,
    WAIT_FOR_EVENT,
    FixedClock,
    ReviewFactory,
    http_client,
    line_json,
    message_json,
    next_push,
    work_pushed,
    one_line_file,
    open_session,
    page_client,
    pointed_json,
    pushes_until,
    repository_opening,
    review_facts,
    thread_json,
    thread_route,
    turn_json,
    until_the_review_holds_threads,
)

MESSAGE = message_json("Run the tests and say what fails.", images=[])

# A moment on the review's clock, in epoch milliseconds
A_MOMENT = 1_791_000_000_000
# How long after it was sent the reader takes a message back, in milliseconds
TAKEN_BACK_AFTER = 40_000
# A file the agent makes after the diff was taken, and one it has yet to make
MADE_SINCE = "made_since.py"
NOT_YET_MADE = "src/not_yet.py"

THREAD = thread_json(
    {**line_json(REVIEWED_FILE, 42), "quote": ["    return now - self.started_at > timeout"]},
    "Why did you drop the None check?",
    turns=[turn_json(TurnAuthor.AUTHOR, "It moved to the caller.", turn_id="turn-1")],
)

QUESTION = {"question_id": FIRST_THREAD_ID, "thread": THREAD}

POINT_ROUTE = "/api/point"


def _pointing(lines: dict[str, object], body: str) -> dict[str, object]:
    """A thread the author raises, as its command sends it: an ordinary note."""
    return {"lines": lines, "body": body, "severity": CommentSeverity.NOTE}


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


def test_every_page_hears_what_the_agent_was_handed_of_a_thread_a_message_points_at(review_page: TestClient) -> None:
    """Carried with the message, the thread is the agent's to read as it was: its opening and the answer under it."""
    with open_session(review_page) as socket:
        review_page.post("/api/message", json={**MESSAGE, "threads": [THREAD]})

        handed = next_push(socket, HandedPush).handed[FIRST_THREAD_ID]

    assert [turn.turn_id for turn in handed.turns] == ["turn-1"]


async def test_a_message_pointing_at_a_thread_quoting_fewer_lines_than_it_names_is_refused(
    client: AsyncClient,
) -> None:
    """Handed over, the agent would take the quote for every line the thread names."""
    short = {**THREAD, "anchor": {**line_json(REVIEWED_FILE, 40, 42), "quote": ["only line 40"]}}

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
        pushed = next_push(socket, ChatPush)

    assert (pushed.message_id, pushed.body, pushed.files) == ("panel-1", "One failed; fixed and green.", [])


async def test_a_page_opening_reads_what_was_said_in_the_panel(client: AsyncClient) -> None:
    """Said before any page was open, or in another browser: a page opening draws it as it was said."""
    await client.post("/api/message", json={**MESSAGE, "threads": [THREAD]})
    await client.post(
        "/api/say", json={"message_id": "panel-1", "body": "One failed; fixed.", "files": [REVIEWED_FILE]}
    )

    asked, answered = (await client.get(CONVERSATION_ROUTE)).json()["said"]

    assert (asked["said_id"], asked["author"], asked["body"]) == ("panel-1", "reader", MESSAGE["body"])
    assert (asked["threads"], asked["taken_back_at"]) == ([FIRST_THREAD_ID], None)
    assert (answered["author"], answered["message_id"], answered["body"]) == ("author", "panel-1", "One failed; fixed.")
    assert answered["files"] == [REVIEWED_FILE]


async def test_a_page_opening_before_anything_was_said_reads_nothing(client: AsyncClient) -> None:
    assert (await client.get(CONVERSATION_ROUTE)).json() == {"said": []}


def test_what_the_agent_says_reaches_a_page_by_the_id_the_review_holds_it_by(review_page: TestClient) -> None:
    """A page that heard it, then reads the conversation as it opens again, draws it once."""
    with open_session(review_page) as socket:
        review_page.post("/api/say", json={"body": "Tests are green again."})
        pushed = next_push(socket, ChatPush)

    [held] = review_page.get(CONVERSATION_ROUTE).json()["said"]

    assert held["said_id"] == pushed.said_id


async def test_what_the_agent_says_is_never_known_by_the_id_of_what_it_said_in_another_review(
    reviews: ReviewFactory,
) -> None:
    """A page's draft outlives the review it was kept from: a review on the same files later must not name its words alike."""
    said_ids = []
    for _ in range(2):
        async with http_client(reviews.app_of_change([one_line_file()])) as agent:
            await agent.post("/api/say", json={"body": "Done."})
            said_ids.append((await agent.get(CONVERSATION_ROUTE)).json()["said"][0]["said_id"])

    first, second = said_ids
    assert first != second


async def test_a_message_taken_back_is_held_as_taken_back_and_when(reviews: ReviewFactory) -> None:
    """A page opening later says it was taken back, and how long ago, as the page that took it back did."""
    clock = FixedClock(A_MOMENT)
    async with http_client(reviews.app_of_change([one_line_file()], clock=clock)) as client:
        await client.post("/api/message", json=MESSAGE)
        clock.moment = A_MOMENT + TAKEN_BACK_AFTER
        await client.post("/api/cancel", json={"message_id": PANEL_MESSAGE_ID})

        [held] = (await client.get(CONVERSATION_ROUTE)).json()["said"]

    assert held["taken_back_at"] == A_MOMENT + TAKEN_BACK_AFTER


async def test_a_message_the_agent_answered_cannot_be_taken_back(client: AsyncClient) -> None:
    """The answer is there to read: a take-back crossing it would strike out what was answered, and ask it dropped."""
    await client.post("/api/message", json=MESSAGE)
    await client.post(EVENTS_ROUTE, params=WAIT_FOR_EVENT)
    await client.post("/api/say", json={"message_id": PANEL_MESSAGE_ID, "body": "Two fail."})

    refused = await client.post("/api/cancel", json={"message_id": PANEL_MESSAGE_ID})
    [asked, _answer] = (await client.get(CONVERSATION_ROUTE)).json()["said"]
    picked_up = (await client.post(EVENTS_ROUTE, params=GLANCE_AT_EVENTS)).json()

    assert (refused.status_code, asked["taken_back_at"], picked_up["type"]) == (HTTPStatus.CONFLICT, None, "timeout")


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
                "lines": pointed_json(REVIEWED_FILE, 1),
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


def test_every_page_hears_that_the_agent_has_the_thread_it_raised(review_page: TestClient) -> None:
    """Its opening is the agent's own words from the moment it is raised, as a page with no draft is told too."""
    with open_session(review_page) as socket:
        review_page.post(POINT_ROUTE, json=_pointing(pointed_json(REVIEWED_FILE, 1), "Kept on purpose"))

        handed = next_push(socket, HandedPush).handed["raised-1"]

    assert (handed.opening.author, handed.opening.body) == (TurnAuthor.AUTHOR, "Kept on purpose")


async def test_a_thread_the_agent_raised_can_be_answered_in(client: AsyncClient) -> None:
    """The reader may ask about it like any other, and the review knows it before the page says it holds it."""
    raised = await client.post(POINT_ROUTE, json=_pointing(pointed_json(REVIEWED_FILE, 1), "Kept on purpose"))

    response = await client.post("/api/reply", json={"thread_id": raised.json()["thread_id"], "body": "Because"})

    assert response.status_code == HTTPStatus.NO_CONTENT


async def test_raised_threads_are_numbered_apart_from_the_readers(client: AsyncClient) -> None:
    """The browser mints its own ids; two sides must not collide."""
    first = await client.post(POINT_ROUTE, json=_pointing(pointed_json(REVIEWED_FILE, 1), "one"))
    second = await client.post(POINT_ROUTE, json=_pointing(pointed_json(REVIEWED_FILE, 1), "two"))

    assert first.json()["thread_id"] == "raised-1"
    assert second.json()["thread_id"] == "raised-2"


async def test_a_thread_on_a_file_not_under_review_is_refused(client: AsyncClient) -> None:
    """Silently accepting it shows the reader a thread about nothing."""
    response = await client.post(POINT_ROUTE, json=_pointing(pointed_json("src/elsewhere.py", 1), "here"))

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "not in this review" in response.json()["detail"]
    assert REVIEWED_FILE in response.json()["detail"]


async def test_a_thread_on_a_line_the_diff_does_not_show_is_refused(client: AsyncClient) -> None:
    """The quote would come back empty and go outdated at the next retake."""
    response = await client.post(POINT_ROUTE, json=_pointing(pointed_json(REVIEWED_FILE, 900), "far away"))

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert "does not show new line 900" in response.json()["detail"]


def test_the_agent_may_speak_first(review_page: TestClient) -> None:
    """Work finished while the reader reads is news they should not have to ask for."""
    with open_session(review_page) as socket:
        review_page.post("/api/say", json={"body": "Tests are green again.", "files": ["src/cli.py"]})
        pushed = next_push(socket, ChatPush)

    assert pushed.message_id is None
    assert pushed.files == ["src/cli.py"]


@pytest.mark.parametrize(
    ("route", "said"),
    [("/api/say", {"body": "Split it out."}), ("/api/progress", {"text": "creating it"})],
    ids=["said", "worked-on"],
)
async def test_the_agent_may_name_a_file_the_diff_does_not_hold(
    client: AsyncClient, route: str, said: dict[str, str]
) -> None:
    """One it is about to make, or has made since the diff was taken: the page says it is not in the diff yet."""
    response = await client.post(route, json={**said, "files": [NOT_YET_MADE]})

    assert response.status_code == HTTPStatus.NO_CONTENT


async def test_the_reader_is_taken_only_to_a_file_the_review_holds(tmp_git_repo: Path, reviews: ReviewFactory) -> None:
    """A file made since the diff was taken is drawn nowhere yet: there is nothing to take the reader to."""
    (tmp_git_repo / "initial.txt").write_text("changed\n")

    async with http_client(reviews.app(await repository_opening(tmp_git_repo))) as agent:
        (tmp_git_repo / MADE_SINCE).write_text("x = 1\n")
        response = await agent.post("/api/show", json={"file": MADE_SINCE})

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_what_is_being_done_is_said_while_it_is_done(review_page: TestClient) -> None:
    """Waiting says only that something is happening; this says what."""
    with open_session(review_page) as socket:
        review_page.post(
            "/api/progress",
            json={"message_id": "panel-1", "text": "rewriting the answer handler", "files": ["a.ts", "b.ts"]},
        )
        work = work_pushed(socket)

    assert work.text == "rewriting the answer handler"
    assert work.files == ["a.ts", "b.ts"]
    assert work.message_id == "panel-1"


def test_work_that_branched_is_reported_as_branches(review_page: TestClient) -> None:
    """Three subagents are three branches, not a sentence about three subagents."""
    with open_session(review_page) as socket:
        review_page.post(
            "/api/progress",
            json={
                "text": "looking for other callers",
                "steps": [{"text": "ran the tests", "done": True}, {"text": "three subagents out", "done": False}],
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
        page_client(reviews.app_of_change([one_line_file()], clock=FixedClock(A_MOMENT))) as review_page,
        open_session(review_page) as socket,
    ):
        review_page.post("/api/progress", json={"text": "reading the handler"})
        work = work_pushed(socket)

    assert work.at == A_MOMENT


def test_a_review_opened_while_work_is_under_way_is_told_what_is_being_done(review_page: TestClient) -> None:
    """A push is gone once sent, and a reload must not lose the line saying what the agent is doing."""
    review_page.post("/api/progress", json={"text": "rewriting the answer handler", "files": ["a.ts"]})

    work = review_facts(review_page).work

    assert work is not None
    assert work.text == "rewriting the answer handler"
    assert work.files == ["a.ts"]


@pytest.mark.parametrize("nothing", ["", " \n"])
def test_a_report_that_says_nothing_says_the_work_is_over(review_page: TestClient, nothing: str) -> None:
    """Nothing at all, or blanks alone: there is no work in either to show."""
    with open_session(review_page) as socket:
        review_page.post("/api/progress", json={"text": "reading the handler"})
        next_push(socket, ProgressPush)
        review_page.post("/api/progress", json={"text": nothing})

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
    async with http_client(reviews.app_of_change([one_line_file()], clock=FixedClock(A_MOMENT))) as client:
        await client.post("/api/status", json={"model": "opus-5"})
        standing = (await client.get(REVIEW_ROUTE)).json()

    assert standing["agent"]["at"] == A_MOMENT


async def test_what_is_said_in_the_panel_is_dated_when_it_was_said(reviews: ReviewFactory) -> None:
    async with http_client(reviews.app_of_change([one_line_file()], clock=FixedClock(A_MOMENT))) as client:
        await client.post("/api/message", json=MESSAGE)
        await client.post("/api/say", json={"message_id": MESSAGE["message_id"], "body": "Two fail."})
        panel = (await client.get(CATCH_UP_ROUTE)).json()["panel"]

    assert [entry["at"] for entry in panel] == [A_MOMENT, A_MOMENT]


async def test_no_status_is_reported_as_nothing_rather_than_zero(client: AsyncClient) -> None:
    """A number nobody sent is a lie; the panel shows it as unknown."""
    standing = (await client.get(REVIEW_ROUTE)).json()

    assert standing["agent"] == {"model": None, "context": None, "at": None}


A_DISCUSSED_THREAD = thread_json(
    {**line_json(REVIEWED_FILE, 1), "quote": [REVIEWED_LINE]},
    "Why did you drop the None check?",
    severity=CommentSeverity.QUESTION,
    turns=[turn_json(TurnAuthor.AUTHOR, "It moved to the caller.", turn_id="turn-1")],
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
