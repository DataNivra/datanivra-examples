# 25 — Developer: approved data in a private sandbox

**Status:** illustrative · **Industry:** Cross-industry · **Language:** Bash · **Framework:** DataNivra CLI · **CI:** none (laptop) · **Fulfilment:** `BUILD_DATASET` · **Profile:** [`edge-cases-core`](../../profiles/edge-cases-core.yaml)

All data is synthetic. DataNivra provisions approved test data into a customer-controlled target; it does not
run these tests. Credentials for the target are never returned by DataNivra — your runner holds its own.

## Why test data matters
Developers debug faster on realistic data, but must not copy production to a laptop.

## What is requested
The profile defaults (200 normal and 100 boundary records).

## Policy gates
Synthetic-only; the target is the approved sandbox environment named by the profile.

## What is provisioned
A certified synthetic dataset in that environment.

## Expected output
`AUTO_APPROVED`, then `READY`.

## Cleanup
`datanivra test-data release <id>` when done.

## Files
* `request.yaml`
* `sandbox.sh`

## Run
1. A tenant administrator defines and a second person approves the profile
   (`datanivra test-data define ../../profiles/edge-cases-core.yaml --submit`, then `datanivra policies approve`).
2. `datanivra test-data validate request.yaml && datanivra test-data plan request.yaml`
3. Run the example with `DATANIVRA_BASE_URL` and a session or workload token.
