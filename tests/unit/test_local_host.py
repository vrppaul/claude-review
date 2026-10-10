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
        pytest.param("localhost:1:2", False, id="a port after a port"),
        pytest.param("localhost.example.com:8000", False, id="a name that only starts like this machine's"),
    ],
)
def test_a_host_is_this_machine_only_when_all_of_it_before_the_port_says_so(host: str, *, local: bool) -> None:
    assert is_local_host(host) is local
