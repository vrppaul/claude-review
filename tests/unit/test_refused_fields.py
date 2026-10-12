"""Functional requirement tests for how a refused field is named to whoever sent it.

The review names a field under the part of the request it came in, as
FastAPI does. That part says nothing to whoever typed a command or filled a
field: they are told the field by what they wrote.
"""

import pytest

from claude_review.presentation.wire.refusal import FieldRefusal, RequestPart

WHY = "says nothing"


@pytest.mark.parametrize("part", [RequestPart.BODY, RequestPart.QUERY, RequestPart.PATH])
def test_a_refused_field_is_named_without_the_part_of_the_request_it_came_in(part: RequestPart) -> None:
    refused = FieldRefusal(loc=(part, "anchor", "file"), msg=WHY)

    assert refused.without_request_part().loc == ("anchor", "file")


def test_a_field_called_what_a_part_of_a_request_is_called_keeps_its_name() -> None:
    """Only the head of its place is the part it came in: a document may well have a field called `path`."""
    refused = FieldRefusal(loc=(RequestPart.BODY, "path"), msg=WHY)

    assert refused.without_request_part().loc == ("path",)


def test_a_field_that_came_in_no_request_is_named_as_it_is() -> None:
    """What a command finds wrong before it sends anything is named from the document's own root."""
    refused = FieldRefusal(loc=("chapters", 0, "title"), msg=WHY)

    assert refused.without_request_part().loc == ("chapters", 0, "title")


def test_what_is_wrong_with_the_whole_of_a_body_has_no_field_left_to_name() -> None:
    refused = FieldRefusal(loc=(RequestPart.BODY,), msg=WHY)

    assert refused.without_request_part().loc == ()
