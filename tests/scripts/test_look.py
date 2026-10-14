"""`scripts/look.py`: a look at the review's page, run as it is run.

A look is a process of its own. It serves a long change with a story told
of it, opens it in a browser, takes the steps it was handed, and prints a
line of what is there as the page opens and after each step. Most of what
is asked of it here is read off one look at the story, one at the files and
one at a change left untold, since each is a server and a browser started.
"""

import asyncio
import contextlib
import os
import re
import signal
import sys
import zlib
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import URL, AsyncClient, ConnectError
from pydantic import BaseModel, ConfigDict

from claude_review.presentation.wire.content import DiffResponse
from claude_review.presentation.wire.story import StoryResponse
from tests.helpers import DIFF_ROUTE, STORY_ROUTE
from tests.page_socket import PageSocket

REPOSITORY = Path(__file__).parents[2]
LOOK = REPOSITORY / "scripts" / "look.py"
# Where a repository keeps two sources of its page, and the page as it was built, from its root
A_SOURCE = "frontend/src/lib/changed.ts"
AN_OLDER_SOURCE = "frontend/src/styles/kept.css"
THE_BUILT_PAGE = "src/claude_review/static/dist/index.html"
# A moment a source was last written at, and one and two minutes before it, as the clock files are stamped by counts them
WRITTEN_AT = 1_700_000_000
A_MINUTE_BEFORE = WRITTEN_AT - 60
TWO_MINUTES_BEFORE = WRITTEN_AT - 120
# What a look says of a page it will not look at: how it is built
HOW_IT_IS_BUILT = "`cd frontend && pnpm build`"
# How long a look may take before it is cut: several times what one takes
LOOK_SECONDS = 60
# What a look exits with: looked, a step not taken, and asked for what it cannot read
LOOKED = 0
NOT_TAKEN = 1
NOT_UNDERSTOOD = 2
# And with when it is stopped from outside, as a shell says of a program stopped at Ctrl-C; how long it has to stop
STOPPED = 130
STOPPED_WITHIN_SECONDS = 10
# Where everything a look starts is told to keep its temporary files
TEMPORARY_FILES_VARIABLE = "TMPDIR"

# What parts the values of a line
BETWEEN_VALUES = " | "
# What a line opens with as the page opens, and a kept look's line of where it is: the word, then the address
OPENED_AT = "open http://"
KEPT = "kept"
# The steps of the one look at the story, and the picture the last of them keeps
SCROLLED_BY = 900
STORY_STEPS = [f"scroll:{SCROLLED_BY}", "press:go-to-part:3", "key:Tab", "shot:deep", "press:hide-contents"]
# What the line says of the parts read through while the reader has scrolled past none
NOTHING_READ = "read: none"
# Steps enough to be under way for seconds: each waits for the page to come to rest
MANY_STEPS = ["key:j"] * 40
STORY_SHOT = "deep.png"
# The look at the files: dark, on a narrow window, one picture kept
NARROW = 700
FILES_SHOT = "narrow.png"
# Its steps: the picture, then the keyboard taken to the first line and a comment begun on it; the comment
# written and added; the area scrolled screens down from it; `n`, which glides back up to the comment; and a
# key that does nothing, for a line after the glide's
FAR_BELOW = 20_000
FILES_STEPS = [
    "shot:narrow",
    "key:j",
    "key:Enter",
    "key:x",
    "key:Control+Enter",
    f"scroll:{FAR_BELOW}",
    "key:n",
    "key:Shift",
]
# The look at a change left untold, by its files. Its steps: the review's agent waits, and the field of
# the panel a reader writes to it in is pressed; the agent tells the story, and the reader reads it
UNTOLD_STEPS = ["agent:wait", "press:panel-input", "agent:story", "press:read-as-story"]
# How tall the window of every look is
WINDOW_HEIGHT = 900
# What a line says of the reading area and of what holds the keyboard, value by value
AREA_SAID = re.compile(
    r"area: (?P<test_id>\S+) scrollTop=(?P<scroll_top>\d+) height=(?P<height>\d+) holds=(?P<holds>\d+)"
)
KEYBOARD_SAID = re.compile(
    r"keyboard: (?P<tag>\S+) testid=(?P<test_id>\S+) label=(?P<label>.+) "
    r"ringed=(?P<ringed>yes|no) box=(?P<width>\d+)x(?P<height>\d+)"
)
# How wide the window is unless a look asks
WIDTH_UNLESS_ASKED = 1440
# What the long change holds: its files, the chapters of the story told of it, and what the first is called
FILES_OF_THE_CHANGE = 41
CHAPTERS_OF_THE_STORY = 6
FIRST_CHAPTER = "The first file added, and the first changed"

# How a PNG opens, where its header says how wide it is, and what names the chunk its pixels are packed in
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_WIDTH = slice(16, 20)
PNG_PIXELS = b"IDAT"
# The first row of a PNG's pixels opens with a byte that says how the row is packed, then the first
# pixel as it is, whatever that byte says: red, green and blue
ROW_PACKING = 1
COLOURS = 3


class Looked(BaseModel):
    """A look that ran to its end: what it exited with, the lines it printed, and what it said went wrong."""

    model_config = ConfigDict(frozen=True)

    exit_code: int
    lines: list[str]
    complaint: str


class Said(BaseModel):
    """One line of a look, value by value in the order the line gives them."""

    model_config = ConfigDict(frozen=True)

    step: str
    page: str
    area: str
    keyboard: str
    bar: str
    read: str
    reading: str


class LookWithShots(BaseModel):
    """A look that kept pictures: what it said, line by line, and the directory it kept them in."""

    model_config = ConfigDict(frozen=True)

    said: list[Said]
    shots: Path


class KeptLook(BaseModel):
    """A look that stays for a reader: where it says the review is, and its process."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    address: str
    process: asyncio.subprocess.Process


class LookUnderWay(BaseModel):
    """A look with its browser open: where its review is, its process, and where its temporary files go."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    address: str
    process: asyncio.subprocess.Process
    temporary: Path


class NotPressed(BaseModel):
    """A press that cannot be taken: what stands in its way, what the look is asked, and what it says of it."""

    model_config = ConfigDict(frozen=True)

    what: str
    asked: list[str]
    said: str


PRESSES_NOT_TAKEN = [
    NotPressed(
        what="no element of that test id",
        asked=["press:no-such-thing"],
        said="there is no element of test id no-such-thing on the page",
    ),
    NotPressed(
        what="fewer of them than were counted to",
        asked=["press:go-to-part:99"],
        said="there are 7 elements of test id go-to-part, counted from 0",
    ),
    NotPressed(
        what="one that is there and cannot be pressed",
        # A comment begun on a line and left empty: there is nothing to save, so its button takes no press
        asked=["--view", "files", "key:j", "key:Enter", "press:save-comment"],
        said="the element is there and could not be pressed",
    ),
]


async def _look(*arguments: str) -> Looked:
    """Run a look to its end, as it is run from a shell in the repository's root."""
    return await _look_in(REPOSITORY, *arguments)


async def _look_in(root: Path, *arguments: str) -> Looked:
    """Run a look to its end in a directory, which it takes for the root of the repository whose page it shows."""
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        str(LOOK),
        *arguments,
        cwd=root,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        printed, complaint = await asyncio.wait_for(process.communicate(), timeout=LOOK_SECONDS)
    finally:
        # A look cut short is not left running; one that ended is no longer there to stop
        with contextlib.suppress(ProcessLookupError):
            process.kill()
    return Looked(exit_code=process.returncode, lines=printed.decode().splitlines(), complaint=complaint.decode())


def _said(line: str) -> Said:
    """A line of a look, read value by value: seven of them, or it is not such a line."""
    step, page, area, keyboard, bar, read, reading = line.split(BETWEEN_VALUES)
    return Said(step=step, page=page, area=area, keyboard=keyboard, bar=bar, read=read, reading=reading)


class AreaSaid(BaseModel):
    """What a line says of the reading area: which it is, how far it has scrolled, its height and what it holds."""

    model_config = ConfigDict(frozen=True)

    test_id: str
    scroll_top: int
    height: int
    holds: int


class KeyboardSaid(BaseModel):
    """What a line says of what holds the keyboard: its tag, test id and label, whether ringed, and its box."""

    model_config = ConfigDict(frozen=True)

    tag: str
    test_id: str
    label: str
    ringed: str
    width: int
    height: int


def _area(said: Said) -> AreaSaid:
    return AreaSaid.model_validate(AREA_SAID.fullmatch(said.area).groupdict())


def _keyboard(said: Said) -> KeyboardSaid:
    return KeyboardSaid.model_validate(KEYBOARD_SAID.fullmatch(said.keyboard).groupdict())


def _first_pixel(picture: Path) -> bytes:
    """The colour of a picture's top left corner."""
    png = picture.read_bytes()
    packed_from = png.index(PNG_PIXELS) + len(PNG_PIXELS)
    row = zlib.decompressobj().decompress(png[packed_from:], ROW_PACKING + COLOURS)
    return row[ROW_PACKING:]


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def story_look(tmp_path_factory: pytest.TempPathFactory) -> LookWithShots:
    """One look at the story: a scroll, a press on the fourth entry of the contents, a key, and a picture."""
    shots = tmp_path_factory.mktemp("story") / "shots"
    looked = await _look("--shots", str(shots), *STORY_STEPS)
    assert looked.exit_code == LOOKED, looked.complaint
    return LookWithShots(said=[_said(line) for line in looked.lines], shots=shots)


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def files_look(tmp_path_factory: pytest.TempPathFactory) -> LookWithShots:
    """One look at the files, dark and on a narrow window, with a picture of how they open."""
    shots = tmp_path_factory.mktemp("files") / "shots"
    looked = await _look(
        "--view", "files", "--theme", "dark", "--width", str(NARROW), "--shots", str(shots), *FILES_STEPS
    )
    assert looked.exit_code == LOOKED, looked.complaint
    return LookWithShots(said=[_said(line) for line in looked.lines], shots=shots)


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def untold_look() -> list[Said]:
    """One look at a change left untold, by its files: its agent waits, and then tells the story."""
    looked = await _look("--untold", "--view", "files", *UNTOLD_STEPS)
    assert looked.exit_code == LOOKED, looked.complaint
    return [_said(line) for line in looked.lines]


@pytest.fixture
async def look_under_way(tmp_path: Path) -> AsyncIterator[LookUnderWay]:
    """A look with its page open and steps under way: enough of them to last for seconds."""
    temporary = tmp_path / "temporary"
    temporary.mkdir()
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        str(LOOK),
        *MANY_STEPS,
        cwd=REPOSITORY,
        env={**os.environ, TEMPORARY_FILES_VARIABLE: str(temporary)},
        stdout=asyncio.subprocess.PIPE,
    )
    opened = _said((await asyncio.wait_for(process.stdout.readline(), timeout=LOOK_SECONDS)).decode())
    _, address = opened.step.split()
    yield LookUnderWay(address=address, process=process, temporary=temporary)
    # One that did not end when it was told to is ended outright
    with contextlib.suppress(ProcessLookupError):
        process.kill()
    await process.wait()


@pytest.fixture
async def kept_look() -> AsyncIterator[KeptLook]:
    """A look kept for a reader, stopped after the test as a shell stops one."""
    process = await asyncio.create_subprocess_exec(
        sys.executable, str(LOOK), "--keep", cwd=REPOSITORY, stdout=asyncio.subprocess.PIPE
    )
    said = await asyncio.wait_for(process.stdout.readline(), timeout=LOOK_SECONDS)
    kept, address = said.decode().split()
    assert kept == KEPT
    yield KeptLook(address=address, process=process)
    with contextlib.suppress(ProcessLookupError):
        process.terminate()
    await process.wait()


async def test_a_look_says_what_is_there_as_the_page_opens_and_again_after_every_step(
    story_look: LookWithShots,
) -> None:
    opened, *after_steps = story_look.said

    assert opened.step.startswith(OPENED_AT)
    assert [said.step for said in after_steps] == STORY_STEPS


async def test_a_page_that_holds_its_place_is_said_to_be_no_taller_than_its_window_and_not_scrolled(
    story_look: LookWithShots,
) -> None:
    assert {said.page for said in story_look.said} == {"page: taller=0 scrolled=0"}


async def test_a_scroll_moves_the_reading_area_by_as_many_pixels(story_look: LookWithShots) -> None:
    opened, scrolled, *_ = story_look.said

    assert opened.area.startswith("area: story-view scrollTop=0 ")
    assert scrolled.area.startswith(f"area: story-view scrollTop={SCROLLED_BY} ")


async def test_a_press_lands_on_the_one_of_its_test_id_that_was_counted_to(story_look: LookWithShots) -> None:
    """Counted from nothing, as Playwright counts: the overview is entry 0, so entry 3 is the third chapter."""
    _, _, pressed, *_ = story_look.said

    assert pressed.reading.startswith("reading: Chapter 3:")


async def test_a_key_is_pressed_on_the_page_and_the_line_says_what_holds_the_keyboard(
    story_look: LookWithShots,
) -> None:
    """Only a key rings what holds the keyboard: nothing is ringed as the page opens, and Tab rings where it lands."""
    opened, _, _, tabbed, *_ = story_look.said

    assert _keyboard(opened).ringed == "no"
    assert _keyboard(tabbed).ringed == "yes"
    assert _keyboard(tabbed).test_id != "none"


async def test_the_line_says_what_the_chapter_bar_says_and_that_there_is_none(story_look: LookWithShots) -> None:
    """No chapter's head has left the screen as the page opens; 900 pixels down, the first chapter's has."""
    opened, scrolled, *_ = story_look.said

    assert opened.bar == "bar: none"
    assert FIRST_CHAPTER in scrolled.bar


async def test_the_line_says_which_parts_are_read_through_and_which_is_being_read(story_look: LookWithShots) -> None:
    """The story opens on its overview, read through only once the reader has scrolled past it."""
    opened, scrolled, *_ = story_look.said

    assert opened.read == NOTHING_READ
    assert opened.reading.startswith("reading: Overview")
    assert scrolled.read.startswith("read: Overview")
    assert scrolled.reading.startswith("reading: Chapter 1:")


async def test_a_shot_is_kept_under_its_name_in_the_directory_asked_for(story_look: LookWithShots) -> None:
    picture = (story_look.shots / STORY_SHOT).read_bytes()

    assert picture.startswith(PNG_SIGNATURE)
    assert int.from_bytes(picture[PNG_WIDTH]) == WIDTH_UNLESS_ASKED


async def test_a_look_stops_the_server_it_started(story_look: LookWithShots) -> None:
    opened, *_ = story_look.said
    _, address = opened.step.split()

    async with AsyncClient(base_url=address) as anybody:
        with pytest.raises(ConnectError):
            await anybody.get("/")


async def test_the_files_are_looked_at_when_they_are_asked_for(files_look: LookWithShots) -> None:
    opened, shot, *_ = files_look.said

    assert opened.area.startswith("area: diff-view ")
    assert shot.area.startswith("area: diff-view ")


async def test_the_line_says_how_tall_the_reading_area_is(story_look: LookWithShots, files_look: LookWithShots) -> None:
    """On the narrow window the header takes a row more, so the area under it is the shorter of the two."""
    wide, *_ = story_look.said
    narrow, *_ = files_look.said

    assert 0 < _area(narrow).height < _area(wide).height < WINDOW_HEIGHT


async def test_the_line_says_how_much_the_reading_area_holds(files_look: LookWithShots) -> None:
    """The long change is many screens tall, and a comment begun on a line makes it taller."""
    opened, _, _, commenting, *_ = files_look.said

    assert _area(commenting).holds > _area(opened).holds > _area(opened).height


async def test_the_line_says_what_holds_the_keyboard_by_its_tag_its_label_and_its_box(
    story_look: LookWithShots, files_look: LookWithShots
) -> None:
    """Three holders in turn: the switch that chose the story, an entry of the contents, the field of a comment."""
    opened, _, pressed, *_ = story_look.said
    _, _, _, commenting, *_ = files_look.said
    switch, entry, field = _keyboard(opened), _keyboard(pressed), _keyboard(commenting)

    assert (switch.tag, switch.test_id, switch.label) == ("BUTTON", "read-as-story", "none")
    assert (entry.tag, entry.test_id) == ("BUTTON", "go-to-part")
    assert entry.label.startswith('"Chapter 3:')
    assert (field.tag, field.test_id) == ("TEXTAREA", "comment-input")
    assert switch.width < entry.width < field.width
    assert switch.height < entry.height < field.height


async def test_a_line_is_printed_once_the_page_has_come_to_rest(files_look: LookWithShots) -> None:
    """`n` glides back up to the comment from screens below it; the step after finds the area where n's own line said."""
    *_, scrolled, glided, after_the_glide = files_look.said

    assert _area(glided).scroll_top < _area(scrolled).scroll_top
    assert glided.area == after_the_glide.area


async def test_the_window_is_as_wide_as_was_asked(files_look: LookWithShots) -> None:
    picture = (files_look.shots / FILES_SHOT).read_bytes()

    assert int.from_bytes(picture[PNG_WIDTH]) == NARROW


async def test_a_dark_look_is_darker_than_a_light_one(story_look: LookWithShots, files_look: LookWithShots) -> None:
    light = _first_pixel(story_look.shots / STORY_SHOT)
    dark = _first_pixel(files_look.shots / FILES_SHOT)

    assert sum(dark) < sum(light)


async def test_a_step_that_cannot_be_taken_ends_the_look_and_is_named() -> None:
    looked = await _look("press:no-such-thing", "key:j")

    assert looked.exit_code == NOT_TAKEN
    assert "press:no-such-thing" in looked.complaint
    # The page as it opened, and nothing of the step after the one not taken
    (only_line,) = looked.lines
    assert _said(only_line).step.startswith(OPENED_AT)


@pytest.mark.parametrize("not_pressed", PRESSES_NOT_TAKEN, ids=lambda not_pressed: not_pressed.what)
async def test_a_press_that_cannot_be_taken_says_which_of_three_things_stood_in_its_way(
    not_pressed: NotPressed,
) -> None:
    looked = await _look(*not_pressed.asked)

    assert looked.exit_code == NOT_TAKEN
    assert not_pressed.said in looked.complaint


async def test_a_shot_with_no_directory_to_keep_it_in_is_refused_before_anything_is_started() -> None:
    looked = await _look("shot:nowhere")

    assert looked.exit_code == NOT_UNDERSTOOD
    assert "shot:nowhere" in looked.complaint
    assert "--shots" in looked.complaint
    assert looked.lines == []


async def test_the_line_says_that_the_contents_are_put_away_where_it_cannot_say_what_is_read(
    story_look: LookWithShots,
) -> None:
    """What is read is said by the contents; with them put away the page says it nowhere a look can read."""
    *_, put_away = story_look.said

    assert put_away.read == "read: contents put away"
    assert put_away.reading == "reading: contents put away"


@pytest.mark.parametrize("written", ["wave:hello", "agent:dance"], ids=["no such kind of step", "no such command"])
async def test_what_is_not_a_step_is_refused_by_name_before_anything_is_started(written: str) -> None:
    looked = await _look(written)

    assert looked.exit_code == NOT_UNDERSTOOD
    assert written in looked.complaint
    assert looked.lines == []


async def test_a_change_left_untold_has_no_part_of_a_story_to_go_to() -> None:
    """Told, the story lists its parts where it is read, and a look presses one of them: `press:go-to-part:3`."""
    looked = await _look("--untold", "--view", "files", "press:read-as-story", "press:go-to-part")

    assert looked.exit_code == NOT_TAKEN
    assert "there is no element of test id go-to-part on the page" in looked.complaint


async def test_a_look_at_an_untold_change_asked_for_as_its_story_opens_on_the_pages_question_and_goes_on() -> None:
    """A look's reader is new to the review: stories are off, and the page asks before a story is written.

    The look goes on from the question: answered, the page shows where the story will be.
    """
    looked = await _look("--untold", "press:turn-on-stories")

    assert looked.exit_code == LOOKED, looked.complaint
    opened, answered = [_said(line) for line in looked.lines]
    assert opened.area.startswith("area: diff-view ")
    assert _keyboard(opened).test_id == "turn-on-stories"
    assert answered.area.startswith("area: story-view ")


async def test_the_reviews_agent_waits_in_a_look_and_the_reader_can_write_to_it(untold_look: list[Said]) -> None:
    """The panel offers its field only while an agent is attached, and an agent is attached once it has waited."""
    _, _, written_to, *_ = untold_look

    assert _keyboard(written_to).test_id == "panel-input"


async def test_the_reviews_agent_tells_the_story_in_a_look_while_the_page_is_open(untold_look: list[Said]) -> None:
    *_, read_as_story = untold_look

    assert read_as_story.area.startswith("area: story-view ")
    assert read_as_story.reading.startswith("reading: Overview")


def _written_at(root: Path, path: str, moment: int) -> None:
    """Write a file of a repository, stamped as last written at a moment."""
    (root / path).parent.mkdir(parents=True)
    (root / path).write_text("")
    os.utime(root / path, (moment, moment))


async def test_a_page_built_before_its_sources_were_last_written_is_not_looked_at(tmp_path: Path) -> None:
    """A look at it would be a look at the page as it was, said of the page as it is.

    One source written since the build is enough, whatever was written before it: the last written is what counts.
    """
    _written_at(tmp_path, AN_OLDER_SOURCE, TWO_MINUTES_BEFORE)
    _written_at(tmp_path, A_SOURCE, WRITTEN_AT)
    _written_at(tmp_path, THE_BUILT_PAGE, A_MINUTE_BEFORE)

    looked = await _look_in(tmp_path, "key:j")

    assert looked.exit_code == NOT_TAKEN
    assert A_SOURCE in looked.complaint
    assert HOW_IT_IS_BUILT in looked.complaint
    assert looked.lines == []


async def test_a_page_that_was_never_built_is_not_looked_at(tmp_path: Path) -> None:
    _written_at(tmp_path, A_SOURCE, WRITTEN_AT)

    looked = await _look_in(tmp_path, "key:j")

    assert looked.exit_code == NOT_TAKEN
    assert HOW_IT_IS_BUILT in looked.complaint
    assert looked.lines == []


async def test_a_look_run_where_there_is_no_page_says_where_it_is_run(tmp_path: Path) -> None:
    looked = await _look_in(tmp_path, "key:j")

    assert looked.exit_code == NOT_TAKEN
    assert "in the repository's root" in looked.complaint
    assert looked.lines == []


async def test_a_look_kept_for_a_reader_takes_no_steps() -> None:
    looked = await _look("--keep", "key:j")

    assert looked.exit_code == NOT_UNDERSTOOD
    assert "--keep" in looked.complaint
    assert looked.lines == []


async def test_a_look_kept_for_a_reader_serves_the_long_change_and_its_story_until_the_page_is_closed(
    kept_look: KeptLook,
) -> None:
    """Read as its page reads it, by the review's routes and its socket: a test of a script drives no browser."""
    async with AsyncClient(base_url=kept_look.address) as reader:
        diff = DiffResponse.model_validate_json((await reader.get(DIFF_ROUTE)).content)
        told = StoryResponse.model_validate_json((await reader.get(STORY_ROUTE)).content)
    page = await asyncio.to_thread(PageSocket, URL(kept_look.address).port)

    page.close()

    assert (len(diff.files), len(told.held.story.chapters)) == (FILES_OF_THE_CHANGE, CHAPTERS_OF_THE_STORY)
    assert await asyncio.wait_for(kept_look.process.wait(), timeout=LOOK_SECONDS) == LOOKED


async def test_a_look_stopped_from_outside_stops_its_server(kept_look: KeptLook) -> None:
    kept_look.process.send_signal(signal.SIGTERM)
    await asyncio.wait_for(kept_look.process.wait(), timeout=LOOK_SECONDS)

    async with AsyncClient(base_url=kept_look.address) as anybody:
        with pytest.raises(ConnectError):
            await anybody.get("/")


async def test_a_look_stopped_with_its_browser_open_ends_at_once_and_leaves_nothing_behind(
    look_under_way: LookUnderWay,
) -> None:
    """Its server, its browser and its own directory all keep what they write where temporary files go."""
    look_under_way.process.send_signal(signal.SIGTERM)

    assert await asyncio.wait_for(look_under_way.process.wait(), timeout=STOPPED_WITHIN_SECONDS) == STOPPED
    async with AsyncClient(base_url=look_under_way.address) as anybody:
        with pytest.raises(ConnectError):
            await anybody.get("/")
    assert list(look_under_way.temporary.iterdir()) == []
