# 04 — Insurance claim payout edge cases

**Status:** illustrative · **Industry:** Insurance · **Language:** Java · **Framework:** JUnit 5 · **CI:** any · **Fulfilment:** `BUILD_DATASET` · **Profile:** [`insurance-claims`](../../profiles/insurance-claims.yaml)

All data is synthetic. DataNivra provisions approved test data into a customer-controlled target; it does not
run these tests. Credentials for the target are never returned by DataNivra — your runner holds its own.

## Why test data matters
Payout calculations fail at deductible and limit boundaries; those cases are rare in a sample.

## What is requested
`insurance-claims@1` with `INS_EVERYDAY_BOOK` × 200, `INS_CLAIM_PAYMENT_EDGE_CASES` × 100.

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
* `ClaimPayoutTest.java`

## Run
1. A tenant administrator defines and a second person approves the profile
   (`datanivra test-data define ../../profiles/insurance-claims.yaml --submit`, then `datanivra policies approve`).
2. `datanivra test-data validate request.yaml && datanivra test-data plan request.yaml`
3. Run the example with `DATANIVRA_BASE_URL` and a session or workload token.
