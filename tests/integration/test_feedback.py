"""The issue the review writes of the reader's feedback, as the page asks for it before anything goes."""

from http import HTTPStatus
from importlib.metadata import version

from claude_review.presentation.schemas.feedback import MAX_FEEDBACK_WORDS, MAX_PART_NAME_LENGTH, MAX_PIXELS
from claude_review.services.feedback import THIS_OPERATING_SYSTEM
from tests.helpers import ReviewFactory, http_client

WORDS = "The tree forgets a folder I folded."
# The browser a reader on Linux reads the page in, as it names itself
CHROME = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
# Feedback as long as the API takes it, with everything that may go with it, each at the longest it may be written
LONGEST = {
    "kind": "idea",
    "words": "w" * MAX_FEEDBACK_WORDS,
    "with_machine": True,
    "reading": {"view": "story", "theme": "dark", "window_width": MAX_PIXELS, "window_height": MAX_PIXELS},
    "part": {
        "name": "p" * MAX_PART_NAME_LENGTH,
        "left": -MAX_PIXELS,
        "top": -MAX_PIXELS,
        "width": MAX_PIXELS,
        "height": MAX_PIXELS,
    },
}


async def test_the_issue_says_the_release_serving_the_review_and_the_browser_the_page_was_read_in(
    reviews: ReviewFactory,
) -> None:
    sent = {"kind": "bug", "words": WORDS, "with_machine": True, "reading": None, "part": None}
    async with http_client(reviews.app_of_change([])) as client:
        answered = (await client.post("/api/feedback", json=sent, headers={"user-agent": CHROME})).json()

    assert (
        answered["body"] == f"{WORDS}\n\nclaude-review {version('claude-review')}, {THIS_OPERATING_SYSTEM}, Chrome 141"
    )


async def test_the_longest_feedback_is_handed_to_the_agent_as_a_message_the_panel_takes(
    reviews: ReviewFactory,
) -> None:
    async with http_client(reviews.app_of_change([])) as client:
        issue = (await client.post("/api/feedback", json=LONGEST, headers={"user-agent": CHROME})).json()
        handed = await client.post(
            "/api/message", json={"message_id": "m1", "body": issue["for_agent"], "threads": [], "images": []}
        )

    assert handed.status_code == HTTPStatus.NO_CONTENT
