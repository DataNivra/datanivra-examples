# 12 — Privacy: masked fields and leakage canaries

**Status:** illustrative · **Industry:** Privacy · **Language:** Python · **Framework:** pytest · **CI:** any · **Fulfilment:** `LEASE_CERTIFIED_VERSION` · **Profile:** [`warehouse-migration`](../../profiles/warehouse-migration.yaml)

All data is synthetic. DataNivra provisions approved test data into a customer-controlled target; it does not
run these tests. Credentials for the target are never returned by DataNivra — your runner holds its own.

## Why test data matters
A masked dataset must not leak source values into logs, exports or error messages of the application.

## What is requested
A lease of the certified masked version.

## Policy gates
Certified version only; customer-runner-only delivery (masked data is not exported to third parties).

## What is provisioned
The masked copy in an approved target.

## Expected output
`AUTO_APPROVED` (with `dataset.provision`); your test seeds synthetic canary strings and asserts they never appear in application logs.

## Cleanup
Fixture releases the lease.

## Files
* `request.yaml`
* `example.py`
* `test_with_datanivra.py`

## Run
1. A tenant administrator defines and a second person approves the profile
   (`datanivra test-data define ../../profiles/warehouse-migration.yaml --submit`, then `datanivra policies approve`).
2. `datanivra test-data validate request.yaml && datanivra test-data plan request.yaml`
3. Run the example with `DATANIVRA_BASE_URL` and a session or workload token.
