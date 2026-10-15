#!/usr/bin/env bash
# Warehouse migration rehearsal — REST with curl + jq (no SDK needed). Needs DATANIVRA_BASE_URL and DATANIVRA_TOKEN.
# DataNivra returns metadata only; connect to the approved target with your own credentials.
set -euo pipefail
API="${DATANIVRA_BASE_URL:?}/v1/test-data/requests"
AUTH=(-H "Authorization: Bearer ${DATANIVRA_TOKEN:?}" -H "Content-Type: application/json")
BODY='{"profile":{"name":"warehouse-migration","version":1},"ttl_seconds":3600}'
created=$(curl -fsS "${AUTH[@]}" -H "Idempotency-Key: ${CI_RUN_KEY:-local-$$}" -d "$BODY" "$API")
id=$(jq -r .id <<<"$created")
release() { curl -fsS "${AUTH[@]}" -d '{"reason_code":"TEST_RUN_FINISHED"}' "$API/$id/release" >/dev/null; }
trap release EXIT
for _ in $(seq 1 120); do
  state=$(curl -fsS "${AUTH[@]}" "$API/$id" | jq -r .state)
  [[ "$state" == READY ]] && break
  [[ "$state" =~ ^(RELEASED|REJECTED|CANCELLED|FAILED)$ ]] && { echo "ended: $state" >&2; exit 26; }
  sleep 5
done
[[ "$state" == READY ]] || { echo "timed out: $state" >&2; exit 27; }
./run-migrations.sh && ./verify-foreign-keys.sh   # your migration tooling, your target credentials
