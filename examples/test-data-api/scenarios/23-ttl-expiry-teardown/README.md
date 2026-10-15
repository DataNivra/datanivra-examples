# 23 — Temporary access expires

**Status:** illustrative · **Industry:** Cross-industry · **Language:** Bash · **Framework:** DataNivra CLI · **CI:** any · **Fulfilment:** `LEASE_CERTIFIED_VERSION` · **Profile:** [`orders-pr-regression`](../../profiles/orders-pr-regression.yaml)

All data is synthetic. DataNivra provisions approved test data into a customer-controlled target; it does not
run these tests. Credentials for the target are never returned by DataNivra — your runner holds its own.

## Why test data matters
Test data must not outlive the run that needed it.

## What is requested
A 15-minute lease.

## Policy gates
TTL within the profile (and the envelope for CI).

## What is provisioned
An isolated copy with a deadline.

## Expected output
After 15 minutes the request reads `RELEASED` with lease state `EXPIRED`.

## Cleanup
Automatic teardown by the TTL sweeper.

## Files
* `request.yaml`
* `ttl.sh`

## Run
1. A tenant administrator defines and a second person approves the profile
   (`datanivra test-data define ../../profiles/orders-pr-regression.yaml --submit`, then `datanivra policies approve`).
2. `datanivra test-data validate request.yaml && datanivra test-data plan request.yaml`
3. Run the example with `DATANIVRA_BASE_URL` and a session or workload token.
