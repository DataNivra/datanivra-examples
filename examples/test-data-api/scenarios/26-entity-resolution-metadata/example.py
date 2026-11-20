"""Entity resolution metadata — provision masked data with cross-system identity columns.

DataNivra can append two columns to every table that participates in an approved identity graph:

  _dn_entity_resolution_key      — a stable, deterministic pseudonym that identifies the same
                                   real entity across tables and datasets; use it as a join key
                                   in tests that exercise cross-system entity matching.

  _dn_entity_resolution_sources  — a JSON array of source system names that contributed identity
                                   evidence for this entity (e.g. '["ehr","billing","claims"]').

Both columns are NULL for rows not covered by the identity graph.

Requirements:
  - The profile must reference an approved identity graph (identity_graph field in the profile).
  - Agent ≥ 0.6.2 is required; earlier versions do not support the column-injection code.
  - Set include_entity_resolution_metadata: true in the request (shown here) or pin it in the
    profile definition so every invocation gets the columns automatically.

See request.yaml in this directory for the manifest, and the docs for the full reference:
  https://www.datanivra.com/docs/entity-resolution
"""

from __future__ import annotations

from pathlib import Path

from datanivra_contracts.testdata import TestDataRequest
from datanivra_sdk import DataNivraClient
from datanivra_sdk.testdata import TestDataClient

REQUEST = Path(__file__).with_name("request.yaml")


def provision(api: DataNivraClient, *, idempotency_key: str | None = None) -> TestDataRequest:
    """Create (or, for the same key, return) the request; DENIED raises ``DataNivraApiError``.

    After the request reaches READY, the target tables will contain:

        patient_id | first_name | ... | _dn_entity_resolution_key        | _dn_entity_resolution_sources
        -----------+------------+-----+----------------------------------+-------------------------------
        10001      | Synthetic  | ... | dn:erk:3f8a1b2c4d5e6f7a8b9c0d1e | ["ehr","billing"]
        10002      | Synthetic  | ... | dn:erk:7c2d3e4f5a6b7c8d9e0f1a2b | ["ehr"]

    The same real entity always produces the same _dn_entity_resolution_key across datasets
    (as long as the masking key and identity graph are unchanged), so you can use it as a
    stable cross-system join key in your test assertions.
    """
    return TestDataClient(api).request(REQUEST, idempotency_key=idempotency_key)


def assert_entity_resolution_columns_present(rows: list[dict]) -> None:
    """Example assertion helper: confirm both columns are present and well-formed.

    ``rows`` is a list of dicts fetched from a provisioned table in the target database.
    """
    import json

    for row in rows:
        # Every row touching the identity graph must have a resolution key.
        assert "_dn_entity_resolution_key" in row, "Missing _dn_entity_resolution_key"
        assert "_dn_entity_resolution_sources" in row, "Missing _dn_entity_resolution_sources"

        key = row["_dn_entity_resolution_key"]
        sources_raw = row["_dn_entity_resolution_sources"]

        if key is not None:
            assert isinstance(key, str) and key.startswith("dn:erk:"), (
                f"Unexpected key format: {key!r}"
            )
        if sources_raw is not None:
            sources = json.loads(sources_raw)
            assert isinstance(sources, list) and len(sources) >= 1, (
                f"Expected non-empty source list, got: {sources_raw!r}"
            )
