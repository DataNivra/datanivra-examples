# 06 — Manufacturing lot recall traceability

**Status:** illustrative · **Industry:** Manufacturing · **Language:** C# · **Framework:** NUnit · **CI:** any · **Fulfilment:** `BUILD_DATASET` · **Profile:** [`manufacturing-traceability`](../../profiles/manufacturing-traceability.yaml)

All data is synthetic. DataNivra provisions approved test data into a customer-controlled target; it does not
run these tests. Credentials for the target are never returned by DataNivra — your runner holds its own.

## Why test data matters
A recall must find every work order and finished good built from an affected lot.

## What is requested
`manufacturing-traceability@1` with `MFG_EVERYDAY_PRODUCTION` × 200, `MFG_LOT_RECALL` × 50.

## Policy gates
Within the profile maximums; synthetic-only.

## What is provisioned
A certified synthetic dataset in the profile's approved target.

## Expected output
`AUTO_APPROVED` for a developer; the test polls until `READY`.

## Cleanup
The `finally`/teardown block calls `POST /v1/test-data/requests/{id}/release`.

## Files
* `request.yaml`
* `LotRecallTests.cs`

## Run
1. A tenant administrator defines and a second person approves the profile
   (`datanivra test-data define ../../profiles/manufacturing-traceability.yaml --submit`, then `datanivra policies approve`).
2. `datanivra test-data validate request.yaml && datanivra test-data plan request.yaml`
3. Run the example with `DATANIVRA_BASE_URL` and a session or workload token.
