#!/usr/bin/env bash
# Parallel pull requests — each matrix job leases its own copy of the same certified version.
# In GitHub Actions run one job per PR (or matrix entry); every job does:
set -euo pipefail
id=$(datanivra test-data request request.yaml --ci-from-env --wait -o json | jq -r .id)
trap 'datanivra test-data release "$id" --reason-code TEST_RUN_FINISHED' EXIT
datanivra test-data status "$id" -o json | jq '{environment_id, state}'   # a different environment per job
./run-integration-tests.sh   # your tests, your approved database access
# Exit codes: 24 denied, 25 still pending approval, 26 ended, 27 timed out (see datanivra --help).
