"""The event loop the browser tests of a run share, and how a fixture is put in it.

A run launches Chromium once, and a browser is driven from the event loop
it was launched in and from no other. So that loop is the run's, and
whatever of a browser test awaits runs in it: the test, which `conftest.py`
puts there, and every async fixture the test asks for, which says so itself
by being declared with `in_the_browsers_loop` where another test's fixture
has `pytest.fixture`. One declared the plain way runs in a loop of its own,
as the other tests and their fixtures do. A review started there would
answer nobody, for that loop stands still while the test runs, so
`ReviewServers.start` refuses it: the loop is not the one the test's
`servers` were made in.
"""

from functools import partial

import pytest_asyncio

# The scope of the loop the browser lives in, as pytest-asyncio names it: one loop for the whole run
BROWSERS_LOOP = "session"

# How an async fixture of a browser test is declared, the one way: bare over a fixture a test has for
# itself, or called with what pytest takes for any fixture, as one kept for a module (`scope="module"`)
# or had by every test (`autouse=True`)
in_the_browsers_loop = partial(pytest_asyncio.fixture, loop_scope=BROWSERS_LOOP)
