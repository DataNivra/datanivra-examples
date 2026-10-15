# 18 — Agent-driven bug reproduction with a pinned request

**Status:** runnable in repo test · **Industry:** Cross-industry · **Language:** Python · **Framework:** pytest · **CI:** any · **Fulfilment:** `BUILD_DATASET` · **Profile:** [`healthcare-integration`](../../profiles/healthcare-integration.yaml)

All data is synthetic. DataNivra provisions approved test data into a customer-controlled target; it does not
run these tests. Credentials for the target are never returned by DataNivra — your runner holds its own.

## Why test data matters
A coding agent that reproduces a bug must get exactly the same data definition on every attempt.

## What is requested
100 routine-care and 50 claim-denial members, pinned to profile version 1.

## Policy gates
Pinned profile version (and optionally its checksum); same request, same `request_checksum`.

## What is provisioned
A certified synthetic dataset.

## Expected output
`planTestDataRequest` returns the same `request_checksum` every time; the created request records it.

## Cleanup
Fixture releases.

## Files
* `request.yaml`
* `example.py`
* `test_with_datanivra.py`

## Run
1. A tenant administrator defines and a second person approves the profile
   (`datanivra test-data define ../../profiles/healthcare-integration.yaml --submit`, then `datanivra policies approve`).
2. `datanivra test-data validate request.yaml && datanivra test-data plan request.yaml`
3. Run the example with `DATANIVRA_BASE_URL` and a session or workload token.
