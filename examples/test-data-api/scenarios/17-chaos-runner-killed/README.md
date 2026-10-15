# 17 — Chaos: the runner is killed mid-test

**Status:** illustrative · **Industry:** Cross-industry · **Language:** Python · **Framework:** pytest · **CI:** any · **Fulfilment:** `LEASE_CERTIFIED_VERSION` · **Profile:** [`orders-pr-regression`](../../profiles/orders-pr-regression.yaml)

All data is synthetic. DataNivra provisions approved test data into a customer-controlled target; it does not
run these tests. Credentials for the target are never returned by DataNivra — your runner holds its own.

## Why test data matters
A killed runner never calls release; the data must still be cleaned up.

## What is requested
A 10-minute lease.

## Policy gates
TTL within the profile.

## What is provisioned
An isolated copy that expires on its own.

## Expected output
Without a release, the lease expires after 10 minutes, the request becomes `RELEASED` (lease state `EXPIRED`) and the pool target is free again. Covered by a lease-expiry test in DataNivra's control-plane test suite.

## Cleanup
Automatic (TTL sweeper); the shared certified version is untouched.

## Files
* `request.yaml`
* `example.py`
* `test_with_datanivra.py`

## Run
1. A tenant administrator defines and a second person approves the profile
   (`datanivra test-data define ../../profiles/orders-pr-regression.yaml --submit`, then `datanivra policies approve`).
2. `datanivra test-data validate request.yaml && datanivra test-data plan request.yaml`
3. Run the example with `DATANIVRA_BASE_URL` and a session or workload token.
