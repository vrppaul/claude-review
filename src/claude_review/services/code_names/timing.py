"""How long a step of reading names took, as the name lookup and the names a change touched log it."""

# A step is timed in seconds and logged in milliseconds
MILLISECONDS_PER_SECOND = 1000


def milliseconds_between(began: float, ended: float) -> int:
    """How long from one `time.perf_counter()` reading to a later one, in whole milliseconds."""
    return round((ended - began) * MILLISECONDS_PER_SECOND)
