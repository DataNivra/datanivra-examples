# 24 — Consumer/provider contract testing

**Status:** illustrative · **Industry:** Cross-industry · **Language:** TypeScript · **Framework:** Pact · **CI:** any · **Fulfilment:** `BUILD_DATASET` · **Profile:** [`retail-orders`](../../profiles/retail-orders.yaml)

All data is synthetic. DataNivra provisions approved test data into a customer-controlled target; it does not
run these tests. Credentials for the target are never returned by DataNivra — your runner holds its own.

## Why test data matters
Provider verification needs provider states backed by data that matches the consumer's expectations.

## What is requested
100 everyday orders for the provider states.

## Policy gates
Within the profile.

## What is provisioned
A certified synthetic dataset behind the provider.

## Expected output
`AUTO_APPROVED`.

## Cleanup
Release after verification.

## Files
* `request.yaml`
* `provider.pact.ts`

## Run
1. A tenant administrator defines and a second person approves the profile
   (`datanivra test-data define ../../profiles/retail-orders.yaml --submit`, then `datanivra policies approve`).
2. `datanivra test-data validate request.yaml && datanivra test-data plan request.yaml`
3. Run the example with `DATANIVRA_BASE_URL` and a session or workload token.
