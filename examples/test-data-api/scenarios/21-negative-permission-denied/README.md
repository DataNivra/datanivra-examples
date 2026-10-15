# 21 — Negative test: an unnamed identity is denied

**Status:** runnable in repo test · **Industry:** Security · **Language:** Python · **Framework:** pytest · **CI:** any · **Fulfilment:** `LEASE_CERTIFIED_VERSION` · **Profile:** [`orders-pr-regression`](../../profiles/orders-pr-regression.yaml)

All data is synthetic. DataNivra provisions approved test data into a customer-controlled target; it does not
run these tests. Credentials for the target are never returned by DataNivra — your runner holds its own.

## Why test data matters
Permission tests prove the guardrails: an identity the profile does not name gets nothing.

## What is requested
A lease by a CI workload identity that the profile's envelope does not list.

## Policy gates
The envelope names the allowed workload identities.

## What is provisioned
Nothing.

## Expected output
`403 TEST_DATA_REQUEST_DENIED`, detail `WORKLOAD_NOT_PERMITTED_BY_PROFILE`; the identity cannot even list the profile.

## Cleanup
Nothing to clean up.

## Files
* `request.yaml`
* `example.py`

## Run
1. A tenant administrator defines and a second person approves the profile
   (`datanivra test-data define ../../profiles/orders-pr-regression.yaml --submit`, then `datanivra policies approve`).
2. `datanivra test-data validate request.yaml && datanivra test-data plan request.yaml`
3. Run the example with `DATANIVRA_BASE_URL` and a session or workload token.
