# 07 — SaaS multi-tenant isolation regression

**Status:** type-checked · **Industry:** SaaS · **Language:** TypeScript · **Framework:** Playwright · **CI:** any · **Fulfilment:** `BUILD_DATASET` · **Profile:** [`edge-cases-core`](../../profiles/edge-cases-core.yaml)

All data is synthetic. DataNivra provisions approved test data into a customer-controlled target; it does not
run these tests. Credentials for the target are never returned by DataNivra — your runner holds its own.

## Why test data matters
Isolation bugs appear only when several tenants hold similar-looking records side by side.

## What is requested
`edge-cases-core@1`: 400 normal and 100 boundary records.

## Policy gates
Within the profile; synthetic-only.

## What is provisioned
A certified synthetic dataset.

## Expected output
`AUTO_APPROVED`; the test runs once the request is `READY`.

## Cleanup
`withTestData` releases the request even when the test fails.

## Files
* `request.yaml`
* `tenant-isolation.spec.ts`

## Run
1. A tenant administrator defines and a second person approves the profile
   (`datanivra test-data define ../../profiles/edge-cases-core.yaml --submit`, then `datanivra policies approve`).
2. `datanivra test-data validate request.yaml && datanivra test-data plan request.yaml`
3. Run the example with `DATANIVRA_BASE_URL` and a session or workload token.
