# 03 — Banking: insufficient funds and duplicate payments

**Status:** runnable in repo test · **Industry:** Banking · **Language:** Python · **Framework:** pytest · **CI:** any · **Fulfilment:** `BUILD_DATASET` · **Profile:** [`banking-regression`](../../profiles/banking-regression.yaml)

All data is synthetic. DataNivra provisions approved test data into a customer-controlled target; it does not
run these tests. Credentials for the target are never returned by DataNivra — your runner holds its own.

## Why test data matters
Payment services must reject insufficient funds and de-duplicate retried transactions; both need accounts with balances at the boundary and transaction pairs that look alike.

## What is requested
`banking-regression@1`: 500 everyday, 200 failed-payment and 50 duplicate-transaction records.

## Policy gates
Within the profile; for CI workload identities the envelope allows at most 1,500 records and is strict (`escalate_out_of_envelope: false`): larger CI requests are denied, not queued.

## What is provisioned
A certified synthetic accounts-and-payments dataset.

## Expected output
Developer: `AUTO_APPROVED` (750 records). CI identity asking for 1,600 records: `DENIED`, detail `TOTAL_EXCEEDS_ENVELOPE`.

## Cleanup
Fixture releases the request after the session.

## Files
* `request.yaml`
* `example.py`
* `test_with_datanivra.py`

## Run
1. A tenant administrator defines and a second person approves the profile
   (`datanivra test-data define ../../profiles/banking-regression.yaml --submit`, then `datanivra policies approve`).
2. `datanivra test-data validate request.yaml && datanivra test-data plan request.yaml`
3. Run the example with `DATANIVRA_BASE_URL` and a session or workload token.
