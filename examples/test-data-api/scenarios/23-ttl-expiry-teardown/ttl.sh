#!/usr/bin/env bash
# Temporary access expires — request a short lease and watch it end on its own.
set -euo pipefail
id=$(datanivra test-data request request.yaml --wait -o json | jq -r .id)
datanivra test-data status "$id" -o json | jq '{state, expires_at}'
# No release on purpose: after ttl_seconds (15 min) the TTL sweeper ends the lease and tears it down.
sleep 960
datanivra test-data status "$id" -o json | jq '{state, lease_state}'   # RELEASED / EXPIRED
