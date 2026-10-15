#!/usr/bin/env bash
# Developer sandbox — approved synthetic data for local debugging, no production copy.
set -euo pipefail
datanivra login --device --tenant "${DATANIVRA_TENANT:?}"
datanivra test-data validate request.yaml
datanivra test-data plan request.yaml          # decision before anything is created
id=$(datanivra test-data request request.yaml --wait -o json | jq -r .id)
echo "Test data $id is READY in the approved sandbox environment; release it with:"
echo "  datanivra test-data release $id"
