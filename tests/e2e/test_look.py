"""`scripts/look.py`: a look at the review's page, run as it is run.

A look is a process of its own. It serves a long change with a story told
of it, opens it in a browser, takes the steps it was handed, and prints a
line of what is there as the page opens and after each step. Most of what
is asked of it here is read off one look at the story and one at the files,
since each is a server and a browser started.
"""

import asyncio
import contextlib
import signal
import sys
import zlib
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient, ConnectError
from playwright.async_api import Page
from pydantic import BaseModel, ConfigDict

from tests.e2e.browsers_loop import BROWSERS_LOOP, in_the_browsers_loop

LOOK = Path(__file__).parents[2] / "scripts" / "look.py"
# How long a look may take before it is cut: several times what one takes
LOOK_SECONDS = 60
# What a look exits with: looked, a step not taken, and asked for what it cannot read
LOOKED = 0
NOT_TAKEN = 1
NOT_UNDERSTOOD = 2

# What parts the values of a line
BETWEEN_VALUES = " | "
# What a line opens with as the page opens, and a kept look's line of where it is: the word, then the address
OPENED_AT = "open http://"
KEPT = "kept"
# The steps of the one look at the story, and the picture the last of them keeps
SCROLLED_BY = 900
STORY_STEPS = [f"scroll:{SCROLLED_BY}", "press:go-to-part:3", "key:Tab", "shot:deep"]
STORY_SHOT = "deep.png"
# The look at the files: dark, on a narrow window, one picture kept
NARROW = 700
FILES_SHOT = "narrow.png"
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


async def _look(*arguments: str) -> Looked:
    """Run a look to its end, as it is run from a shell."""
    process = await asyncio.create_subprocess_exec(
        sys.executable, str(LOOK), *arguments, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
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


def _first_pixel(picture: Path) -> bytes:
    """The colour of a picture's top left corner."""
    png = picture.read_bytes()
    packed_from = png.index(PNG_PIXELS) + len(PNG_PIXELS)
    row = zlib.decompressobj().decompress(png[packed_from:], ROW_PACKING + COLOURS)
    return row[ROW_PACKING:]


@pytest_asyncio.fixture(scope="module", loop_scope=BROWSERS_LOOP)
async def story_look(tmp_path_factory: pytest.TempPathFactory) -> LookWithShots:
    """One look at the story: a scroll, a press on the fourth entry of the contents, a key, and a picture."""
    shots = tmp_path_factory.mktemp("story") / "shots"
    looked = await _look("--shots", str(shots), *STORY_STEPS)
    assert looked.exit_code == LOOKED, looked.complaint
    return LookWithShots(said=[_said(line) for line in looked.lines], shots=shots)


@pytest_asyncio.fixture(scope="module", loop_scope=BROWSERS_LOOP)
async def files_look(tmp_path_factory: pytest.TempPathFactory) -> LookWithShots:
    """One look at the files, dark and on a narrow window, with a picture of how they open."""
    shots = tmp_path_factory.mktemp("files") / "shots"
    looked = await _look(
        "--view", "files", "--theme", "dark", "--width", str(NARROW), "--shots", str(shots), "shot:narrow"
    )
    assert looked.exit_code == LOOKED, looked.complaint
    return LookWithShots(said=[_said(line) for line in looked.lines], shots=shots)


@in_the_browsers_loop
async def kept_look() -> AsyncIterator[KeptLook]:
    """A look kept for a reader, stopped after the test as a shell stops one."""
    process = await asyncio.create_subprocess_exec(sys.executable, str(LOOK), "--keep", stdout=asyncio.subprocess.PIPE)
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

    assert "ringed=no" in opened.keyboard
    assert "ringed=yes" in tabbed.keyboard
    assert "testid=none" not in tabbed.keyboard


async def test_the_line_says_what_the_chapter_bar_says_and_that_there_is_none(story_look: LookWithShots) -> None:
    """No chapter's head has left the screen as the page opens; 900 pixels down, the first chapter's has."""
    opened, scrolled, *_ = story_look.said

    assert opened.bar == "bar: none"
    assert FIRST_CHAPTER in scrolled.bar


async def test_the_line_says_which_parts_are_read_through_and_which_is_being_read(story_look: LookWithShots) -> None:
    """The overview fits on the screen it opens on, so it is read through as the page opens."""
    opened, scrolled, *_ = story_look.said

    assert opened.read.startswith("read: Overview")
    assert opened.reading.startswith("reading: Overview")
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
    opened, shot = files_look.said

    assert opened.area.startswith("area: diff-view ")
    assert shot.area.startswith("area: diff-view ")


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


async def test_a_shot_with_no_directory_to_keep_it_in_cannot_be_taken() -> None:
    looked = await _look("shot:nowhere")

    assert looked.exit_code == NOT_TAKEN
    assert "shot:nowhere" in looked.complaint
    assert "--shots" in looked.complaint


async def test_what_is_not_a_step_is_refused_by_name_before_anything_is_started() -> None:
    looked = await _look("wave:hello")

    assert looked.exit_code == NOT_UNDERSTOOD
    assert "wave:hello" in looked.complaint
    assert looked.lines == []


async def test_a_look_kept_for_a_reader_takes_no_steps() -> None:
    looked = await _look("--keep", "key:j")

    assert looked.exit_code == NOT_UNDERSTOOD
    assert "--keep" in looked.complaint
    assert looked.lines == []


async def test_a_look_kept_for_a_reader_serves_the_long_change_and_its_story_until_the_page_is_closed(
    kept_look: KeptLook, page: Page
) -> None:
    await page.goto(kept_look.address)
    await page.get_by_test_id("guide-not-now").click()
    assert await page.get_by_test_id("file-item").count() == FILES_OF_THE_CHANGE
    await page.get_by_test_id("read-as-story").click()
    await page.get_by_test_id("story-chapter").first.wait_for()
    assert await page.get_by_test_id("story-chapter").count() == CHAPTERS_OF_THE_STORY

    await page.close()

    assert await asyncio.wait_for(kept_look.process.wait(), timeout=LOOK_SECONDS) == LOOKED


async def test_a_look_stopped_from_outside_stops_its_server(kept_look: KeptLook) -> None:
    kept_look.process.send_signal(signal.SIGTERM)
    await asyncio.wait_for(kept_look.process.wait(), timeout=LOOK_SECONDS)

    async with AsyncClient(base_url=kept_look.address) as anybody:
        with pytest.raises(ConnectError):
            await anybody.get("/")
