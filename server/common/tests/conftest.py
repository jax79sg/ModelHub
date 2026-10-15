import pytest
from modelhub_testkit.issuer import FakeIssuer


@pytest.fixture
def issuer():
    return FakeIssuer()


class Clock:
    """A clock a test can move by hand."""

    def __init__(self, now: float = 1000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock():
    return Clock()
