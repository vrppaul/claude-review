"""Where a review on this machine is reached: on loopback, by its port."""

# The review has no authentication, so it listens on loopback alone:
# reachable from this machine and nowhere else
LOOPBACK = "127.0.0.1"


def review_url(port: int) -> str:
    """The address the review's page is opened at."""
    return f"http://{LOOPBACK}:{port}"
