# GitHub Actions — PR test data with workload identity

[`pr-test-data.yml`](pr-test-data.yml): copy to `.github/workflows/`, and `../request.yaml` to
`.datanivra/request.yaml`. Status: **static-validated** (parsed, actions pinned by SHA, every CLI
command parsed by the real CLI parser, actionlint); not run on GitHub by this repository.

**Prerequisites:** self-hosted runner labelled `datanivra-ci` that can reach the profile's targets;
repository variables `DATANIVRA_BASE_URL`, `DATANIVRA_TENANT`, `DATANIVRA_WORKLOAD_IDENTITY_ID`,
`DATANIVRA_AUDIENCE`; secret `APP_DB_DSN` (the runner's own target access).

**Permissions:** `contents: read` at the top; `id-token: write` only on the two jobs that sign in.
The trust should allow `refs/pull/*` (PR runs) and never `pull_request_target`, which DataNivra
refuses anyway: fork code must not run with your credentials.

**One-time (administrators):**
```bash
datanivra workload-identities create --name "claims CI" --provider GITHUB_ACTIONS \
  --repository acme/claims-service --audience datanivra:acme --ref 'refs/pull/*' --ref refs/heads/main
```
then name the printed trust id in the profile's `automation.workload_identity_ids` (new profile
version, approved by a second person).

**Every run:** OIDC sign-in → `test-data request --ci-from-env` → `test-data wait` → tests →
`test-data release` (`if: always()`, after a fresh sign-in because workload sessions last ≤ 15 min).
On `pull_request: closed` a clean-up job releases any request of that PR still live.

**Cancellation:** a cancelled run still executes the `always()` step; if the runner itself dies,
the lease TTL ends the request.

**Never logged:** the OIDC token and the DataNivra session (stored in `$RUNNER_TEMP`, owner-only).
