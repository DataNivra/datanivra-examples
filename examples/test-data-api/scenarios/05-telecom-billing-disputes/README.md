# 05 — Telecom billing disputes

**Status:** illustrative · **Industry:** Telecom · **Language:** Go · **Framework:** go test · **CI:** any · **Fulfilment:** `BUILD_DATASET` · **Profile:** [`telecom-billing`](../../profiles/telecom-billing.yaml)

All data is synthetic. DataNivra provisions approved test data into a customer-controlled target; it does not
run these tests. Credentials for the target are never returned by DataNivra — your runner holds its own.

## Why test data matters
Dispute handling depends on usage records, bills and adjustments that agree with each other.

## What is requested
`telecom-billing@1` with `TEL_EVERYDAY_USAGE` × 300, `TEL_DISPUTED_BILLS` × 100.

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
* `billing_test.go`

## Run
1. A tenant administrator defines and a second person approves the profile
   (`datanivra test-data define ../../profiles/telecom-billing.yaml --submit`, then `datanivra policies approve`).
2. `datanivra test-data validate request.yaml && datanivra test-data plan request.yaml`
3. Run the example with `DATANIVRA_BASE_URL` and a session or workload token.
