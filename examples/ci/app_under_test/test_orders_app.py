"""The application's own test suite, run by the CI pipeline against the provisioned target.

Configuration (set by the CI job): ``APP_DB_DSN`` and ``APP_DB_SCHEMA`` point at the ephemeral
test database. ``DATANIVRA_CI_DATASET_ID`` / ``DATANIVRA_CI_DATASET_VERSION`` are exported by
``datanivra_ci.py`` so failures can be tied to the exact certified dataset version.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterator
from decimal import Decimal
from typing import Any

import psycopg
import pytest
from orders_app import lifetime_values, top_customers
from psycopg import sql

SCHEMA = os.environ.get("APP_DB_SCHEMA", "public")


@pytest.fixture(scope="module")
def conn() -> Iterator[Any]:
    """One database connection to the provisioned test target, shared by the module's tests."""
    with psycopg.connect(os.environ["APP_DB_DSN"]) as c:
        yield c


def test_pipeline_exports_the_dataset_pin() -> None:
    """The pipeline exported which certified dataset version these tests run against."""
    assert re.fullmatch(r"[0-9a-f-]{36}", os.environ["DATANIVRA_CI_DATASET_ID"])
    assert int(os.environ["DATANIVRA_CI_DATASET_VERSION"]) >= 1


def test_every_order_belongs_to_a_customer(conn: Any) -> None:
    """Subsetting kept referential integrity: no order points at a missing customer."""
    query = sql.SQL(
        "SELECT count(*) FROM {o} o LEFT JOIN {c} c USING (customer_id) WHERE c.customer_id IS NULL"
    ).format(o=sql.Identifier(SCHEMA, "orders"), c=sql.Identifier(SCHEMA, "customer"))
    assert conn.execute(query).fetchone()[0] == 0


def test_lifetime_value_report_matches_the_orders(conn: Any) -> None:
    """The report's totals add up to the orders table and are sorted highest first."""
    values = lifetime_values(conn, SCHEMA)
    assert values, "the provisioned dataset must contain customers"
    total = conn.execute(
        sql.SQL("SELECT coalesce(sum(amount), 0) FROM {}").format(sql.Identifier(SCHEMA, "orders"))
    ).fetchone()[0]
    assert sum((v.total for v in values), Decimal(0)) == Decimal(total)
    assert values == sorted(values, key=lambda v: (-v.total, v.customer_id))
    assert len(top_customers(conn, SCHEMA, 3)) == 3


def test_contact_data_is_masked_test_data(conn: Any) -> None:
    """The app must never see production-looking contacts; masked e-mails keep a valid shape."""
    emails = [
        r[0]
        for r in conn.execute(
            sql.SQL("SELECT email FROM {} WHERE email IS NOT NULL").format(sql.Identifier(SCHEMA, "customer"))
        ).fetchall()
    ]
    assert emails
    assert all("@" in e for e in emails)
    assert not any(e.endswith("@synthetic-int03.invalid") for e in emails), "source e-mails must be masked"
