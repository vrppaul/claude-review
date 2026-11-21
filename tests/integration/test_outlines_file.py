"""Functional requirement tests for the file every review of the user keeps what outlined a file's content in."""

from pathlib import Path

from claude_review.repositories.outlines_file import OutlinesFile

KEY = "generation:0123abcd.py"
OTHER_KEY = "generation:4567ef01.py"
OUTLINE = b'[{"name": "first"}]'
REWRITTEN = b'[{"name": "second"}]'


async def test_what_one_review_kept_another_reads_and_nothing_is_read_where_nothing_was_kept(tmp_path: Path) -> None:
    """The file and its directory are made only once something is kept; keeping again under a key replaces it."""
    path = tmp_path / "cache" / "claude-review" / "names.sqlite"
    before = await OutlinesFile(path).read([KEY])

    await OutlinesFile(path).keep({KEY: OUTLINE})
    await OutlinesFile(path).keep({KEY: REWRITTEN})
    read = await OutlinesFile(path).read([KEY, OTHER_KEY])

    assert (before, read) == ({}, {KEY: REWRITTEN})
