# GitLab CI — MR test data with workload identity

[`.gitlab-ci.yml`](.gitlab-ci.yml). Status: **static-validated** (parsed, CLI commands parsed by
the real CLI parser); not run on GitLab by this repository.

**Prerequisites:** a runner tagged `datanivra-ci` that can reach the profile's targets; CI/CD
variables `DATANIVRA_BASE_URL`, `DATANIVRA_TENANT`, `DATANIVRA_WORKLOAD_IDENTITY_ID`,
`DATANIVRA_WHEELS_URL`, masked `APP_DB_DSN`.

**One-time (administrators):**
```bash
datanivra workload-identities create --name "claims MR" --provider GITLAB_CI \
  --repository acme/claims-service --audience datanivra:acme --ref refs/heads/main --protected-refs-only
```
GitLab's `ref` claim is a branch or tag name; DataNivra normalises it to `refs/heads/...` /
`refs/tags/...`. `--protected-refs-only` refuses tokens whose `ref_protected` is not `true`, so MR
pipelines from unprotected branches cannot get data — loosen it deliberately or not at all.

**Every run:** `id_tokens: DATANIVRA_ID_TOKEN` (audience `datanivra:acme`) → `datanivra login
--workload-identity` → request → wait → tests → `after_script` release.

**Limitation:** GitLab issues one id token per job and DataNivra accepts each token once, so the
`after_script` release reuses the stored session (≤ 15 minutes). For longer jobs the request ends at
the lease TTL instead (still torn down).

**Never logged:** `DATANIVRA_ID_TOKEN` and the session (in `$CI_PROJECT_DIR/.datanivra-config`).
