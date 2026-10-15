# 13 — Financial reconciliation breaks

**Status:** illustrative · **Industry:** Banking · **Language:** Python · **Framework:** pytest · **CI:** any · **Fulfilment:** `BUILD_DATASET` · **Profile:** [`banking-regression`](../../profiles/banking-regression.yaml)

All data is synthetic. DataNivra provisions approved test data into a customer-controlled target; it does not
run these tests. Credentials for the target are never returned by DataNivra — your runner holds its own.

## Why test data matters
Reconciliation jobs must flag breaks and still produce deterministic totals.

## What is requested
500 everyday and 100 reconciliation-break records.

## Policy gates
Within the profile.

## What is provisioned
A certified synthetic dataset.

## Expected output
`AUTO_APPROVED`.

## Cleanup
Fixture releases.

## Files
* `request.yaml`
* `example.py`
* `test_with_datanivra.py`

## Run
1. A tenant administrator defines and a second person approves the profile
   (`datanivra test-data define ../../profiles/banking-regression.yaml --submit`, then `datanivra policies approve`).
2. `datanivra test-data validate request.yaml && datanivra test-data plan request.yaml`
3. Run the example with `DATANIVRA_BASE_URL` and a session or workload token.
