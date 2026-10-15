# 11 — Authorization: cross-account access is refused

**Status:** illustrative · **Industry:** Cross-industry · **Language:** Robot Framework · **Framework:** RequestsLibrary · **CI:** any · **Fulfilment:** `BUILD_DATASET` · **Profile:** [`banking-regression`](../../profiles/banking-regression.yaml)

All data is synthetic. DataNivra provisions approved test data into a customer-controlled target; it does not
run these tests. Credentials for the target are never returned by DataNivra — your runner holds its own.

## Why test data matters
Access-control tests need two owners with similar accounts so a leaked id would be noticed.

## What is requested
200 everyday banking records.

## Policy gates
Within the profile; synthetic-only.

## What is provisioned
A certified synthetic dataset.

## Expected output
`AUTO_APPROVED`; then your suite asserts 403/404 for the other owner's account ids.

## Cleanup
Suite teardown releases the request.

## Files
* `request.yaml`
* `cross_account.robot`

## Run
1. A tenant administrator defines and a second person approves the profile
   (`datanivra test-data define ../../profiles/banking-regression.yaml --submit`, then `datanivra policies approve`).
2. `datanivra test-data validate request.yaml && datanivra test-data plan request.yaml`
3. Run the example with `DATANIVRA_BASE_URL` and a session or workload token.
