# 10 — API pagination and malformed records

**Status:** illustrative · **Industry:** Cross-industry · **Language:** JSON · **Framework:** Postman / Newman · **CI:** any · **Fulfilment:** `BUILD_DATASET` · **Profile:** [`edge-cases-core`](../../profiles/edge-cases-core.yaml)

All data is synthetic. DataNivra provisions approved test data into a customer-controlled target; it does not
run these tests. Credentials for the target are never returned by DataNivra — your runner holds its own.

## Why test data matters
Cursor pagination breaks on page boundaries, empty pages and records with missing fields.

## What is requested
1,000 normal, 100 null-heavy and 50 invalid records.

## Policy gates
Within the profile; synthetic-only.

## What is provisioned
A certified synthetic dataset behind your API.

## Expected output
Collection step 1 receives `201`, step 2 polls until `READY`, the last step releases.

## Cleanup
The collection's final request releases the test-data request.

## Files
* `request.yaml`
* `pagination.postman_collection.json`

## Run
1. A tenant administrator defines and a second person approves the profile
   (`datanivra test-data define ../../profiles/edge-cases-core.yaml --submit`, then `datanivra policies approve`).
2. `datanivra test-data validate request.yaml && datanivra test-data plan request.yaml`
3. Run the example with `DATANIVRA_BASE_URL` and a session or workload token.
