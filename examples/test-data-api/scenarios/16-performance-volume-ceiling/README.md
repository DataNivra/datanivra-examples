# 16 — Performance volume with a hard ceiling

**Status:** illustrative · **Industry:** Cross-industry · **Language:** Python · **Framework:** Locust · **CI:** any · **Fulfilment:** `BUILD_DATASET` · **Profile:** [`edge-cases-core`](../../profiles/edge-cases-core.yaml)

All data is synthetic. DataNivra provisions approved test data into a customer-controlled target; it does not
run these tests. Credentials for the target are never returned by DataNivra — your runner holds its own.

## Why test data matters
Load tests need volume, but an unbounded request could exhaust a shared target.

## What is requested
40,000 high-volume records (profile ceiling 50,000).

## Policy gates
The profile's `max_count` and `max_total_records` are hard ceilings.

## What is provisioned
A certified synthetic dataset.

## Expected output
40,000: `AUTO_APPROVED`. 60,000: `DENIED` with `COUNT_EXCEEDS_PROFILE_MAXIMUM`.

## Cleanup
Release after the load run (`datanivra test-data release <id>`).

## Files
* `request.yaml`
* `locustfile.py`

## Run
1. A tenant administrator defines and a second person approves the profile
   (`datanivra test-data define ../../profiles/edge-cases-core.yaml --submit`, then `datanivra policies approve`).
2. `datanivra test-data validate request.yaml && datanivra test-data plan request.yaml`
3. Run the example with `DATANIVRA_BASE_URL` and a session or workload token.
