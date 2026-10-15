# 22 — Automatic approval vs over-limit requests

**Status:** runnable in repo test · **Industry:** Healthcare · **Language:** Python · **Framework:** pytest · **CI:** GitHub Actions · **Fulfilment:** `BUILD_DATASET` · **Profile:** [`healthcare-integration`](../../profiles/healthcare-integration.yaml)

All data is synthetic. DataNivra provisions approved test data into a customer-controlled target; it does not
run these tests. Credentials for the target are never returned by DataNivra — your runner holds its own.

## Why test data matters
Automation should be fast inside the approved envelope and escalate to a person outside it.

## What is requested
2,700 records: inside the profile (3,000) but over the envelope (2,500).

## Policy gates
Envelope approved with the profile version; automatic approval needs the operator and tenant switches.

## What is provisioned
Nothing until a person approves; then a certified synthetic dataset.

## Expected output
`PENDING_HUMAN_APPROVAL`, reason `TOTAL_EXCEEDS_ENVELOPE`; a second person approves with `datanivra test-data approve <id> --reason ...`.

## Cleanup
Release (cancels while pending).

## Files
* `request.yaml`
* `example.py`

## Run
1. A tenant administrator defines and a second person approves the profile
   (`datanivra test-data define ../../profiles/healthcare-integration.yaml --submit`, then `datanivra policies approve`).
2. `datanivra test-data validate request.yaml && datanivra test-data plan request.yaml`
3. Run the example with `DATANIVRA_BASE_URL` and a session or workload token.
