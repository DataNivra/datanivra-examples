# 09 — Per-PR PostgreSQL lease

**Status:** runnable in repo test · **Industry:** Cross-industry · **Language:** Python · **Framework:** pytest · **CI:** GitHub Actions / GitLab CI · **Fulfilment:** `LEASE_CERTIFIED_VERSION` · **Profile:** [`orders-pr-regression`](../../profiles/orders-pr-regression.yaml)

All data is synthetic. DataNivra provisions approved test data into a customer-controlled target; it does not
run these tests. Credentials for the target are never returned by DataNivra — your runner holds its own.

## Why test data matters
Each pull request needs the same DataNivra-certified data in its own database so parallel builds never interfere.

## What is requested
A 30-minute lease of the certified orders dataset.

## Policy gates
Certified, provisionable version only; target chosen from the approved pool (never by the request); for CI identities the envelope caps the TTL at one hour.

## What is provisioned
An isolated copy in one pool target per request.

## Expected output
`AUTO_APPROVED`, `state` `PROVISIONING` then `READY`; a second concurrent request gets a different `environment_id`.

## Cleanup
Release tears the copy down; the certified version stays `PUBLISHED`.

## Files
* `request.yaml`
* `example.py`
* `test_with_datanivra.py`

## Run
1. A tenant administrator defines and a second person approves the profile
   (`datanivra test-data define ../../profiles/orders-pr-regression.yaml --submit`, then `datanivra policies approve`).
2. `datanivra test-data validate request.yaml && datanivra test-data plan request.yaml`
3. Run the example with `DATANIVRA_BASE_URL` and a session or workload token.
