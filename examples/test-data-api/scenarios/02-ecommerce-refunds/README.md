# 02 — E-commerce refunds and payment declines

**Status:** type-checked · **Industry:** Retail / e-commerce · **Language:** TypeScript · **Framework:** Vitest · **CI:** any · **Fulfilment:** `BUILD_DATASET` · **Profile:** [`retail-orders`](../../profiles/retail-orders.yaml)

All data is synthetic. DataNivra provisions approved test data into a customer-controlled target; it does not
run these tests. Credentials for the target are never returned by DataNivra — your runner holds its own.

## Why test data matters
Refund logic breaks on the rare paths: partial returns, declined payments, orders whose payment failed after reservation. Everyday data alone does not exercise them.

## What is requested
`retail-orders@1` with 300 everyday, 100 return/refund and 50 payment-decline records.

## Policy gates
Counts within the profile maximums; synthetic-only.

## What is provisioned
A certified synthetic orders dataset in the profile's approved target.

## Expected output
`AUTO_APPROVED` for a developer; `state` becomes `READY` once the build is certified.

## Cleanup
`afterAll` releases the request.

## Files
* `request.yaml`
* `refunds.test.ts`

## Run
1. A tenant administrator defines and a second person approves the profile
   (`datanivra test-data define ../../profiles/retail-orders.yaml --submit`, then `datanivra policies approve`).
2. `datanivra test-data validate request.yaml && datanivra test-data plan request.yaml`
3. Run the example with `DATANIVRA_BASE_URL` and a session or workload token.
