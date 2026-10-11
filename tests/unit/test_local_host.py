"""Which Host headers name this machine: the origin guard's first check against a page that rebinds its name."""

import pytest

from claude_review.presentation.origin_guard import is_local_host


@pytest.mark.parametrize(
    ("host", "local"),
    [
        pytest.param("localhost", True, id="a name with no port"),
        pytest.param("localhost:8000", True, id="a name and its port"),
        pytest.param("127.0.0.1:8000", True, id="an address and its port"),
        pytest.param("[::1]:8000", True, id="an IPv6 address in brackets"),
        pytest.param("LocalHost:8000", True, id="a name in any case"),
        # A port forwarded to the review's (ssh, a container) arrives under
        # another number; the Origin, which must match the Host, holds the port
        pytest.param("localhost:1234", True, id="a name and a port other than the one served"),
        pytest.param("localhost:1:2", False, id="a port after a port"),
        pytest.param("localhost:http", False, id="a port that is no number"),
        pytest.param("localhost.example.com:8000", False, id="a name that only starts like this machine's"),
        pytest.param("127.0.0.1.evil", False, id="an address that only starts like this machine's"),
        pytest.param("[::1]evil", False, id="a name after an IPv6 address"),
        pytest.param("[::1]evil.example:8000", False, id="a name and a port after an IPv6 address"),
        pytest.param("user@localhost:8000", False, id="someone named before the name"),
        pytest.param("localhost/evil", False, id="a path after the name"),
        pytest.param("", False, id="no name at all"),
    ],
)
def test_a_host_is_this_machine_only_when_all_of_it_says_so(host: str, *, local: bool) -> None:
    assert is_local_host(host) is local
