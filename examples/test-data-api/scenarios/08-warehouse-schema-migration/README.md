# 08 — Warehouse schema migration rehearsal

**Status:** illustrative · **Industry:** Data warehouse · **Language:** Bash · **Framework:** curl + jq · **CI:** any · **Fulfilment:** `LEASE_CERTIFIED_VERSION` · **Profile:** [`warehouse-migration`](../../profiles/warehouse-migration.yaml)

All data is synthetic. DataNivra provisions approved test data into a customer-controlled target; it does not
run these tests. Credentials for the target are never returned by DataNivra — your runner holds its own.

## Why test data matters
Migrations must keep foreign keys intact on realistic volumes before they touch production.

## What is requested
A one-hour lease of the certified, masked `warehouse-migration` dataset version.

## Policy gates
The certified version must be provisionable; one isolated pool target per rehearsal.

## What is provisioned
The certified version hydrated into a free pool target (secret reference resolved by the agent).

## Expected output
`AUTO_APPROVED` for a caller holding `dataset.provision`; otherwise `PENDING_HUMAN_APPROVAL`.

## Cleanup
`trap release EXIT` releases the lease; the shared certified version is never revoked.

## Files
* `request.yaml`
* `rehearse.sh`

## Run
1. A tenant administrator defines and a second person approves the profile
   (`datanivra test-data define ../../profiles/warehouse-migration.yaml --submit`, then `datanivra policies approve`).
2. `datanivra test-data validate request.yaml && datanivra test-data plan request.yaml`
3. Run the example with `DATANIVRA_BASE_URL` and a session or workload token.
