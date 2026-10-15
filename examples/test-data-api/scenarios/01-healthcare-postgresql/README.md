# 01 — Healthcare integration on PostgreSQL

**Status:** runnable in repo test · **Industry:** Healthcare · **Language:** Python · **Framework:** pytest · **CI:** any · **Fulfilment:** `BUILD_DATASET` · **Profile:** [`healthcare-integration`](../../profiles/healthcare-integration.yaml)

All data is synthetic. DataNivra provisions approved test data into a customer-controlled target; it does not
run these tests. Credentials for the target are never returned by DataNivra — your runner holds its own.

## Why test data matters
Integration tests for scheduling, claims and lab workflows need many related records — members with coverage, encounters, claims and lab results — without ever touching real patient data.

## What is requested
The approved `healthcare-integration@1` profile with its defaults: `HC_ROUTINE_CARE` × 500 and `HC_CHRONIC_CARE` × 2000 (2,500 records in total).

## Policy gates
Profile version approved by a second person; synthetic-only build (no source is read); counts must stay within the profile maximums (500 / 2,000; ceiling 3,000); the automation envelope allows 2,500 records for the named CI workload identity.

## What is provisioned
A certified synthetic dataset built by the customer's agent into the profile's approved PostgreSQL target environment.

## Expected output
| Caller | Request | Decision |
| --- | --- | --- |
| Developer (human) | defaults (2,500) | `AUTO_APPROVED` (synthetic-only builds follow the tenant's approval scope) |
| CI workload identity, both switches on | defaults (2,500) | `AUTO_APPROVED` |
| CI workload identity, automatic approval off (default) | defaults | `PENDING_HUMAN_APPROVAL`, reason `AUTOMATIC_APPROVAL_DISABLED` |
| CI workload identity | + `HC_CLAIM_DENIALS` × 200 (2,700) | `PENDING_HUMAN_APPROVAL`, reason `TOTAL_EXCEEDS_ENVELOPE` |
| anyone | `HC_ROUTINE_CARE` × 600 | `DENIED` (403 `TEST_DATA_REQUEST_DENIED`, detail `COUNT_EXCEEDS_PROFILE_MAXIMUM`) |

## Cleanup
`TestDataClient.acquire` releases the request; releasing a build revokes the dataset that was built for this request alone.

## How the promptbook illustration maps to the real healthcare pack

The design brief spoke of "500 patients and 2,000 appointments". The healthcare pack has no `Patient` or
`Appointment` entity: a **member** is the patient and an **encounter** is the visit (appointment). Scenario counts
are exact numbers of *member* root entities; encounters, claims and labs follow from each scenario's fan-out. This
example therefore requests 500 routine-care members and 2,000 chronic-care members (each with several encounters).
It does not promise an exact number of encounters.

## Files
* `request.yaml`
* `example.py`
* `test_with_datanivra.py`

## Run
1. A tenant administrator defines and a second person approves the profile
   (`datanivra test-data define ../../profiles/healthcare-integration.yaml --submit`, then `datanivra policies approve`).
2. `datanivra test-data validate request.yaml && datanivra test-data plan request.yaml`
3. Run the example with `DATANIVRA_BASE_URL` and a session or workload token.
