"""Schema evolution across certified versions (pytest).

Run in your CI with ``DATANIVRA_BASE_URL`` and a token (``datanivra login --workload-identity ...``
or ``DATANIVRA_TOKEN``). The data is released after the session, even when tests fail.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from datanivra_contracts.testdata import TestDataRequest
from datanivra_sdk import DataNivraClient
from datanivra_sdk.testdata import TestDataClient
from example import REQUEST


@pytest.fixture(scope="session")
def test_data() -> Iterator[TestDataRequest]:
    api = DataNivraClient(os.environ["DATANIVRA_BASE_URL"], token=os.environ["DATANIVRA_TOKEN"])
    with TestDataClient(api).acquire(REQUEST, idempotency_key=os.environ.get("CI_RUN_KEY")) as request:
        yield request


def test_reader_accepts_both_versions(test_data: TestDataRequest) -> None:
    # Your assertions run against your application and the approved target environment
    # ``test_data.environment_id``; DataNivra only returns metadata (ids, states, digests).
    assert test_data.state.value == "READY"
