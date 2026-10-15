# 20 — Schema evolution across certified versions

**Status:** illustrative · **Industry:** Cross-industry · **Language:** Python · **Framework:** pytest · **CI:** any · **Fulfilment:** `LEASE_CERTIFIED_VERSION` · **Profile:** [`warehouse-migration`](../../profiles/warehouse-migration.yaml)

All data is synthetic. DataNivra provisions approved test data into a customer-controlled target; it does not
run these tests. Credentials for the target are never returned by DataNivra — your runner holds its own.

## Why test data matters
Readers must handle data written by the previous and the next schema version.

## What is requested
A lease of the version the profile pins; a new profile version pins the next dataset version.

## Policy gates
Each profile version is reviewed; old pins keep working until deprecated or revoked.

## What is provisioned
The pinned certified version.

## Expected output
`AUTO_APPROVED` (with `dataset.provision`).

## Cleanup
Fixture releases.

## Files
* `request.yaml`
* `example.py`
* `test_with_datanivra.py`

## Run
1. A tenant administrator defines and a second person approves the profile
   (`datanivra test-data define ../../profiles/warehouse-migration.yaml --submit`, then `datanivra policies approve`).
2. `datanivra test-data validate request.yaml && datanivra test-data plan request.yaml`
3. Run the example with `DATANIVRA_BASE_URL` and a session or workload token.
