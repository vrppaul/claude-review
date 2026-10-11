"""E2E: the page runs under the policy it is served with, in a real browser.

The server names the page's inline script by a hash it takes itself; only a
browser can say that it takes the same one. Nothing the page runs may be
refused, and the page says the rest of what a browser may do with it.
"""

from playwright.async_api import Page

from tests.helpers import ReviewServers, one_line_file, opening_of

# What Chromium writes on the console about anything the page's policy refused
REFUSED_BY_THE_POLICY = "Content Security Policy"
# The headers the page is served with that say what a browser may do with it
POLICY_HEADER = "content-security-policy"
SNIFFING_HEADER = "x-content-type-options"
REFERRER_HEADER = "referrer-policy"
# A script the policy lets run by its hash, and the source that would let any inline script run
SCRIPT_BY_HASH = "'sha256-"
ANY_INLINE_SCRIPT = "'unsafe-inline'"


def _script_sources(policy: str) -> list[str]:
    """Where a policy lets scripts come from."""
    directives = [directive.split() for directive in policy.split(";")]
    return next(sources for name, *sources in directives if name == "script-src")


async def test_the_page_runs_its_inline_script_under_its_policy_and_nothing_is_refused(
    servers: ReviewServers, page: Page
) -> None:
    review = await servers.start(opening_of([one_line_file()]))
    console: list[str] = []
    page.on("console", lambda message: console.append(message.text))

    served = await page.goto(review.url)
    await page.wait_for_selector('[data-testid="file-section"]')

    assert served is not None
    scripts = _script_sources(await served.header_value(POLICY_HEADER) or "")
    assert any(source.startswith(SCRIPT_BY_HASH) for source in scripts)
    assert ANY_INLINE_SCRIPT not in scripts
    assert [said for said in console if REFUSED_BY_THE_POLICY in said] == []


async def test_the_page_is_read_as_what_it_says_it_is_and_leaks_no_address(servers: ReviewServers, page: Page) -> None:
    review = await servers.start(opening_of([one_line_file()]))

    served = await page.goto(review.url)

    assert served is not None
    assert await served.header_value(SNIFFING_HEADER) == "nosniff"
    assert await served.header_value(REFERRER_HEADER) == "no-referrer"
