#!/bin/sh
# Generic CI recipe (ADR-0018): POSIX sh + curl + jq against the DataNivra REST API, no SDK.
#
#   DATANIVRA_BASE_URL=https://api.example.test DATANIVRA_TOKEN=... \
#     ./datanivra-test-data.sh ../request.json -- ./scripts/run-integration-tests.sh
#
# Steps: (sign in) -> request -> wait READY -> run your test command -> release (always, via trap).
# Exit codes: the test command's status; 24 denied by the profile; 25 still pending a human approval;
# 26 ended without READY; 27 timed out; 1 other API errors.
#
# Credentials: DATANIVRA_TOKEN (a session), or a workload identity exchange with
# DATANIVRA_ID_TOKEN (your CI's OIDC token) + DATANIVRA_TENANT + DATANIVRA_WORKLOAD_IDENTITY_ID.
# The bearer token is written to a 0600 header file, never put on a command line or printed.
# Only ids, states and reason codes are printed; DataNivra never returns rows or credentials.
set -eu

manifest=${1:?usage: datanivra-test-data.sh REQUEST.json -- TEST COMMAND...}
shift
[ "${1:-}" = "--" ] && shift
: "${DATANIVRA_BASE_URL:?set DATANIVRA_BASE_URL}"
# The token must never travel unencrypted or to another origin: https only (plain http only to a
# loopback control plane), no credentials/query/fragment in the URL; curl never follows redirects
# here (no -L), and a 3xx is treated as a failure.
case "$DATANIVRA_BASE_URL" in
  *@* | *\?* | *\#*) echo "datanivra: DATANIVRA_BASE_URL must not contain credentials, a query or a fragment" >&2; exit 2 ;;
  https://?*) ;;
  http://localhost | http://localhost:[0-9]* | http://localhost/* | http://127.0.0.1 | http://127.0.0.1:[0-9]* | http://127.0.0.1/*) ;;
  *) echo "datanivra: DATANIVRA_BASE_URL must be https://" >&2; exit 2 ;;
esac
timeout=${DATANIVRA_WAIT_SECONDS:-1200}
key=${DATANIVRA_IDEMPOTENCY_KEY:-"sh-$(date +%s)-$$"}

workdir=$(mktemp -d)
chmod 700 "$workdir"
headers="$workdir/headers"
request_id=""

cleanup() {
  status=$?
  if [ -n "$request_id" ]; then
    curl -sS -o /dev/null -X POST -H @"$headers" \
      --data '{"reason_code":"TEST_RUN_FINISHED"}' \
      "$DATANIVRA_BASE_URL/v1/test-data/requests/$request_id/release" || true
    echo "datanivra: released $request_id" >&2
  fi
  rm -rf "$workdir"
  exit "$status"
}
trap cleanup EXIT INT TERM

if [ -z "${DATANIVRA_TOKEN:-}" ]; then
  : "${DATANIVRA_ID_TOKEN:?set DATANIVRA_TOKEN or DATANIVRA_ID_TOKEN}"
  : "${DATANIVRA_TENANT:?}" "${DATANIVRA_WORKLOAD_IDENTITY_ID:?}"
  export DATANIVRA_ID_TOKEN DATANIVRA_TENANT DATANIVRA_WORKLOAD_IDENTITY_ID
  # jq reads the token from its environment, so it never appears in a process argument list.
  jq -n '{id_token: env.DATANIVRA_ID_TOKEN, tenant_slug: env.DATANIVRA_TENANT,
          workload_identity_id: env.DATANIVRA_WORKLOAD_IDENTITY_ID}' > "$workdir/exchange.json"
  DATANIVRA_TOKEN=$(curl -sS --fail -H 'Content-Type: application/json' --data @"$workdir/exchange.json" \
    "$DATANIVRA_BASE_URL/v1/auth/workload/token" | jq -r .access_token)
fi
umask 077
printf 'Authorization: Bearer %s\nContent-Type: application/json\n' "$DATANIVRA_TOKEN" > "$headers"

jq '.spec' "$manifest" > "$workdir/body.json"
http=$(curl -sS -o "$workdir/created.json" -w '%{http_code}' -X POST -H @"$headers" \
  -H "Idempotency-Key: $key" --data @"$workdir/body.json" "$DATANIVRA_BASE_URL/v1/test-data/requests")
case "$http" in
  200 | 201) ;;
  403)
    echo "datanivra: denied: $(jq -r '[.details[].code] | join(", ")' "$workdir/created.json")" >&2
    exit 24
    ;;
  *)
    echo "datanivra: request failed: HTTP $http $(jq -r .code "$workdir/created.json")" >&2
    exit 1
    ;;
esac
request_id=$(jq -r .id "$workdir/created.json")
echo "datanivra: request $request_id decision $(jq -r .decision "$workdir/created.json")" >&2

deadline=$(($(date +%s) + timeout))
delay=2
while :; do
  curl -sS --fail -H @"$headers" "$DATANIVRA_BASE_URL/v1/test-data/requests/$request_id" > "$workdir/state.json"
  state=$(jq -r .state "$workdir/state.json")
  case "$state" in
    READY) break ;;
    RELEASED | REJECTED | CANCELLED | FAILED)
      echo "datanivra: request ended as $state ($(jq -r '.state_reason_code // "no reason"' "$workdir/state.json"))" >&2
      exit 26
      ;;
  esac
  if [ "$(date +%s)" -ge "$deadline" ]; then
    echo "datanivra: still $state after ${timeout}s" >&2
    [ "$state" = PENDING_APPROVAL ] && exit 25
    exit 27
  fi
  sleep "$delay"
  [ "$delay" -lt 30 ] && delay=$((delay * 2))
done

echo "datanivra: READY environment $(jq -r .environment_id "$workdir/state.json")" >&2
"$@"
