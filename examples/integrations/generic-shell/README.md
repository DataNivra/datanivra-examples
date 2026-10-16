# Generic recipes (any CI, any container)

Two equivalent recipes that use only the REST API — no DataNivra SDK or CLI install:

| File | Needs | Status |
| --- | --- | --- |
| [`datanivra-test-data.sh`](datanivra-test-data.sh) | POSIX `sh`, `curl` (≥ 7.55), `jq` | static-validated (shellcheck) |
| [`datanivra_test_data.py`](datanivra_test_data.py) | Python 3.12 standard library | synthetic E2E in repo (in-process control plane + fake agent) |

```bash
export DATANIVRA_BASE_URL=https://api.example.test
export DATANIVRA_TOKEN=...            # or DATANIVRA_ID_TOKEN + DATANIVRA_TENANT + DATANIVRA_WORKLOAD_IDENTITY_ID
export DATANIVRA_IDEMPOTENCY_KEY="ci-$RUN_ID-$ATTEMPT"   # stable per run attempt
./datanivra-test-data.sh ../request.json -- ./scripts/run-integration-tests.sh
python3 datanivra_test_data.py ../request.json -- ./scripts/run-integration-tests.sh
```

Both: request the manifest's `spec` (`POST /v1/test-data/requests`), poll
`GET /v1/test-data/requests/{id}` with back-off until `READY`, run the test command, and release
(`POST .../release`) from a `trap`/`finally` — on success, failure and Ctrl-C/SIGTERM. Exit codes:
the test command's status, 24 denied, 25 pending approval at timeout, 26 ended, 27 timeout, 130/143
cancelled by Ctrl-C/SIGTERM (after the release; the Python recipe also stops the running test
command).

**Never logged:** the token (the shell recipe keeps it in a 0600 header file, not on the command
line), connection details, rows. Use these when your runner has network access to the approved
targets (see `../self-hosted-runner/README.md`).
