"""Healthcare integration on PostgreSQL — provision approved test data through the Python SDK.

``provision`` only asks DataNivra for data from the approved ``healthcare-integration`` profile; your own test
suite runs against the approved target with its own, separately managed database access.
"""

from __future__ import annotations

from pathlib import Path

from datanivra_contracts.testdata import TestDataRequest
from datanivra_sdk import DataNivraClient
from datanivra_sdk.testdata import TestDataClient

REQUEST = Path(__file__).with_name("request.yaml")


def provision(api: DataNivraClient, *, idempotency_key: str | None = None) -> TestDataRequest:
    """Create (or, for the same key, return) the request; DENIED raises ``DataNivraApiError``."""
    return TestDataClient(api).request(REQUEST, idempotency_key=idempotency_key)
