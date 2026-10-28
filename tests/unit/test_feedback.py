"""The issue the review writes of a reader's feedback: to the letter, with only what the reader left ticked."""

from urllib.parse import parse_qs, urlsplit

import pytest

from claude_review.domain.feedback import (
    FeedbackDraft,
    FeedbackKind,
    Machine,
    PartBox,
    PointedPart,
    Reading,
    ReadingView,
    ShownTheme,
)
from claude_review.services.feedback import (
    FILLED_ADDRESS_LONGEST,
    browser_named,
    issue_of,
    operating_system_named,
)

WORDS = "Story and Files switch back to Story every time the page reloads, though I chose Files."
MACHINE = Machine(release="1.6.1", operating_system="Linux", browser="Chrome 141")
READING = Reading(view=ReadingView.FILES, theme=ShownTheme.LIGHT, window_width=1440, window_height=900)
PART = PointedPart(name="the header's view switch › Story", box=PartBox(left=196, top=8, width=74, height=32))
# What goes with the words, each line as the issue writes it
MACHINE_LINE = "claude-review 1.6.1, Linux, Chrome 141"
READING_LINE = "Reading Files, the light theme, a window 1440 × 900"
PART_LINE = "Pointed at the header's view switch › Story, 74 × 32 at 196, 8"
# A first line with no word's end in the room a title has: an address pasted in
ADDRESS_WRITTEN = "http://127.0.0.1:8765/api/diff?base=main&version=round-two&whitespace=ignored&layout=split"
# Words long enough that the address with them in it runs past what GitHub takes
TOO_MANY_WORDS = "word " * (FILLED_ADDRESS_LONGEST // 4)


def _draft(
    words: str = WORDS,
    *,
    kind: FeedbackKind = FeedbackKind.BUG,
    with_machine: bool = False,
    reading: Reading | None = None,
    part: PointedPart | None = None,
) -> FeedbackDraft:
    return FeedbackDraft(kind=kind, words=words, with_machine=with_machine, reading=reading, part=part)


def _query(address: str) -> dict[str, list[str]]:
    return parse_qs(urlsplit(address).query)


@pytest.mark.parametrize(
    ("draft", "title"),
    [
        (_draft("The tree forgets a folder I folded."), "Bug: The tree forgets a folder I folded."),
        (
            _draft("Pin a thread to the panel's top.\nSo the one I wait on stays in sight.", kind=FeedbackKind.IDEA),
            "Idea: Pin a thread to the panel's top.",
        ),
        (_draft("The tree\tforgets  a folder."), "Bug: The tree forgets a folder."),
        (_draft(WORDS), "Bug: Story and Files switch back to Story every time the page reloads, though I…"),
        (_draft(ADDRESS_WRITTEN), "Bug: http://127.0.0.1:8765/api/diff?base=main&version=round-two&whitespace=igno…"),
    ],
)
def test_an_issue_is_titled_by_its_kind_and_the_first_line_written_cut_at_a_word(
    draft: FeedbackDraft, title: str
) -> None:
    assert issue_of(draft, MACHINE).title == title


@pytest.mark.parametrize(
    ("draft", "body"),
    [
        (_draft(), WORDS),
        (_draft(with_machine=True), f"{WORDS}\n\n{MACHINE_LINE}"),
        (_draft(reading=READING), f"{WORDS}\n\n{READING_LINE}"),
        (_draft(part=PART), f"{WORDS}\n\n{PART_LINE}"),
        (
            _draft(with_machine=True, reading=READING, part=PART),
            f"{WORDS}\n\n{MACHINE_LINE}\n{READING_LINE}\n{PART_LINE}",
        ),
    ],
)
def test_an_issue_carries_what_was_written_and_only_what_the_reader_left_ticked(
    draft: FeedbackDraft, body: str
) -> None:
    assert issue_of(draft, MACHINE).body == body


def test_the_issue_opens_on_github_filled_in_to_the_letter() -> None:
    issue = issue_of(_draft(with_machine=True), MACHINE)

    assert (issue.filled, _query(issue.address)) == (True, {"title": [issue.title], "body": [issue.body]})


def test_an_issue_too_long_to_fill_in_opens_with_its_title_alone() -> None:
    issue = issue_of(_draft(TOO_MANY_WORDS), MACHINE)

    assert (issue.filled, _query(issue.address)) == (False, {"title": [issue.title]})


def test_the_agent_is_handed_the_issue_to_file_as_written_once_the_reader_has_seen_it() -> None:
    issue = issue_of(_draft(with_machine=True), MACHINE)

    assert issue.for_agent == (
        "Feedback on claude-review, a bug, for vrppaul/claude-review. Look for an issue like it first, then show me "
        "what you will file: the title and body below as they are, adding nothing of this review. File it only once "
        f"I say so.\n\n{issue.title}\n\n{issue.body}"
    )


@pytest.mark.parametrize(
    ("user_agent", "browser"),
    [
        (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
            "Chrome 141",
        ),
        ("Mozilla/5.0 (X11; Linux x86_64; rv:144.0) Gecko/20100101 Firefox/144.0", "Firefox 144"),
        (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 "
            "Safari/605.1.15",
            "Safari 18",
        ),
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 "
            "Safari/537.36 Edg/141.0.3537.71",
            "Edge 141",
        ),
        (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 "
            "OPR/124.0.0.0",
            "Opera 124",
        ),
        ("curl/8.9.1", None),
        (None, None),
    ],
)
def test_the_browser_is_named_by_its_mark_in_the_user_agent(user_agent: str | None, browser: str | None) -> None:
    assert browser_named(user_agent) == browser


@pytest.mark.parametrize(("platform_name", "named"), [("Darwin", "macOS"), ("Linux", "Linux"), ("Windows", "Windows")])
def test_an_operating_system_is_named_as_its_maker_names_it(platform_name: str, named: str) -> None:
    assert operating_system_named(platform_name) == named
