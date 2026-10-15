from datetime import datetime, timedelta, timezone

import pytest
from modelhub_artifactory_service import db


class FakeClock:
    def __init__(self):
        self.now = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.now

    def advance(self, **kw):
        self.now += timedelta(**kw)


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def pool(fresh_database):
    db.migrate(fresh_database)
    p = db.make_pool(fresh_database)
    yield p
    p.close()
