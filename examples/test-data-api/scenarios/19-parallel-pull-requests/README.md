# 19 — Parallel pull requests share one certified version

**Status:** runnable in repo test · **Industry:** Cross-industry · **Language:** Bash · **Framework:** DataNivra CLI · **CI:** GitHub Actions matrix · **Fulfilment:** `LEASE_CERTIFIED_VERSION` · **Profile:** [`orders-pr-regression`](../../profiles/orders-pr-regression.yaml)

All data is synthetic. DataNivra provisions approved test data into a customer-controlled target; it does not
run these tests. Credentials for the target are never returned by DataNivra — your runner holds its own.

## Why test data matters
Many PRs build at once; each needs its own copy of the same certified version.

## What is requested
One lease per PR from the same profile.

## Policy gates
One live request per pool target; `TARGET_POOL_EXHAUSTED` (409) when every target is busy.

## What is provisioned
Independent copies, one per pool target.

## Expected output
Two concurrent requests get two different `environment_id`s; a fifth concurrent request on a pool of four gets `TARGET_POOL_EXHAUSTED`.

## Cleanup
Each job releases its own request (`if: always()`); release never revokes the shared version.

## Files
* `request.yaml`
* `parallel.sh`

## Run
1. A tenant administrator defines and a second person approves the profile
   (`datanivra test-data define ../../profiles/orders-pr-regression.yaml --submit`, then `datanivra policies approve`).
2. `datanivra test-data validate request.yaml && datanivra test-data plan request.yaml`
3. Run the example with `DATANIVRA_BASE_URL` and a session or workload token.
