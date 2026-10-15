"""A tiny "application under test" for the CI/CD reference pipeline.

It is a stand-in for your service: it reads customers and orders from the database it is
configured with and computes a customer lifetime-value report. In CI that database is the
ephemeral target DataNivra provisioned with certified, masked test data. The application
never talks to DataNivra.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from psycopg import sql


@dataclass(frozen=True)
class CustomerValue:
    """One row of the lifetime-value report: a customer, their order count and total spend."""

    customer_id: int
    orders: int
    total: Decimal


def lifetime_values(conn: Any, schema: str) -> list[CustomerValue]:
    """Orders and total spend per customer (customers without orders included), highest first."""
    query = sql.SQL(
        "SELECT c.customer_id, count(o.order_id), coalesce(sum(o.amount), 0) "
        "FROM {c} c LEFT JOIN {o} o ON o.customer_id = c.customer_id "
        "GROUP BY c.customer_id ORDER BY 3 DESC, 1"
    ).format(c=sql.Identifier(schema, "customer"), o=sql.Identifier(schema, "orders"))
    return [CustomerValue(int(r[0]), int(r[1]), Decimal(r[2])) for r in conn.execute(query).fetchall()]


def top_customers(conn: Any, schema: str, n: int = 5) -> list[CustomerValue]:
    """The ``n`` customers with the highest lifetime value (see :func:`lifetime_values`)."""
    return lifetime_values(conn, schema)[:n]
