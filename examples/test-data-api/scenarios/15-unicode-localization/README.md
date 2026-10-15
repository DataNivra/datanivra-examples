# 15 — Unicode and localization

**Status:** type-checked · **Industry:** Cross-industry · **Language:** TypeScript · **Framework:** Vitest · **CI:** any · **Fulfilment:** `BUILD_DATASET` · **Profile:** [`edge-cases-core`](../../profiles/edge-cases-core.yaml)

All data is synthetic. DataNivra provisions approved test data into a customer-controlled target; it does not
run these tests. Credentials for the target are never returned by DataNivra — your runner holds its own.

## Why test data matters
Length limits, collation and truncation break on multi-byte text.

## What is requested
300 core boundary records (field-length and type boundaries).

## Policy gates
Within the profile.

## What is provisioned
A certified synthetic dataset.

## Expected output
`AUTO_APPROVED`. Which scripts and alphabets appear depends on the generators of your estate; check them in a plan before relying on a specific script.

## Cleanup
`afterAll` releases.

## Files
* `request.yaml`
* `unicode.test.ts`

## Run
1. A tenant administrator defines and a second person approves the profile
   (`datanivra test-data define ../../profiles/edge-cases-core.yaml --submit`, then `datanivra policies approve`).
2. `datanivra test-data validate request.yaml && datanivra test-data plan request.yaml`
3. Run the example with `DATANIVRA_BASE_URL` and a session or workload token.
