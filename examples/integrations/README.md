# CI/CD integrations for the Test Data API

Thin, copyable recipes that let a pipeline **request approved test data, wait for it, run its own
tests and release it** — through the DataNivra CLI or REST API only. They add no logic of their own:
the DataNivra control plane decides (`AUTO_APPROVED`, `PENDING_HUMAN_APPROVAL`, `DENIED`) from the
second-person-approved profile, and your customer-resident DataNivra agent hydrates and tears down
the target. Rows never pass through the CI system; only ids, states and reason codes do.

These are examples of compatibility through standard APIs, not official vendor integrations or
partnerships. Every value in them is a synthetic placeholder (`acme/claims-service`,
`datanivra:acme`, `<WORKLOAD_IDENTITY_ID>`).

## Before you start (one-time, by your DataNivra administrators)

1. A DataNivra agent in your network and a certified dataset; an approved test-data **profile**
   (here `claims-pr-regression` v1) whose target pool your runners can reach.
2. For GitHub Actions and GitLab CI: a **workload identity trust** for the repository and audience
   (`datanivra workload-identities create ...`), named in the profile's automation envelope.
   Workload identity and automatic approval are **off by default** and enabled by the DataNivra
   operator only after owner approval. Without automatic approval, requests wait for a human
   (`datanivra test-data approve`); the recipes then end with exit code 25 when they time out.
3. The CLI (`datanivra-cli`) and SDK wheels from your DataNivra release assets — the packages are
   **not published** to PyPI or npm.

The repeatable part (every run) is what the recipes show. The shared manifest is
[`request.yaml`](request.yaml) (JSON twin: [`request.json`](request.json)); validate it with
`datanivra test-data validate request.yaml`.

## Matrix

| Integration | File | Auth | Cleanup | Validated how | Status |
| --- | --- | --- | --- | --- | --- |
| GitHub Actions | [`github-actions/pr-test-data.yml`](github-actions/pr-test-data.yml) | job OIDC token → workload session (`id-token: write`) | `if: always()` release + PR-closed job | YAML, pinned SHAs, CLI argv parsed by the real CLI parser, actionlint | static-validated |
| GitLab CI | [`gitlab-ci/.gitlab-ci.yml`](gitlab-ci/.gitlab-ci.yml) | `id_tokens` → workload session | `after_script` release | YAML, CLI argv parsed | static-validated |
| Jenkins | [`jenkins/Jenkinsfile`](jenkins/Jenkinsfile) | short-lived session token (credential binding) | `post { always }` | CLI argv parsed | illustrative, not run |
| Azure DevOps | [`azure-devops/azure-pipelines.yml`](azure-devops/azure-pipelines.yml) | short-lived session token (secret variable) | `condition: always()` | YAML, CLI argv parsed | illustrative, not run |
| CircleCI | [`circleci/config.yml`](circleci/config.yml) | short-lived session token (context) | `when: always` | YAML, CLI argv parsed | illustrative, not run |
| Generic shell (curl + jq) | [`generic-shell/datanivra-test-data.sh`](generic-shell/datanivra-test-data.sh) | session token or workload exchange | `trap ... EXIT` | shellcheck | static-validated |
| Generic Python (stdlib) | [`generic-shell/datanivra_test_data.py`](generic-shell/datanivra_test_data.py) | session token or workload exchange | `finally` | run against the in-process control plane and a fake agent | synthetic E2E in repo |
| Blacksmith-style runner | [`blacksmith/pr-test-data.yml`](blacksmith/pr-test-data.yml) | GitHub OIDC (as GitHub Actions) | `if: always()` | YAML, actionlint | illustrative, not run — GitHub Actions-compatible runner example, unverified, no Blacksmith dependency |
| Self-hosted runner | [`self-hosted-runner/README.md`](self-hosted-runner/README.md) | any of the above | — | — | guidance |
| Ephemeral Kubernetes | [`kubernetes/README.md`](kubernetes/README.md) | any of the above | lease TTL + namespace teardown | — | guidance |

"static-validated" means the files are parsed and checked by DataNivra's own contract tests; it
does **not** mean the pipeline ran on that CI service. The control-plane behaviour the recipes
rely on (decisions, isolated pool targets, release, TTL expiry, 30 concurrent pull requests) is
covered by DataNivra's control-plane test suite.

## Behaviour every recipe keeps

* **Request → wait → test → release**, with release on success, failure and cancellation. A runner
  killed before releasing is covered by the lease TTL (`ttl_seconds`): the request ends and the agent
  tears the copy down. Releasing never revokes the shared certified version.
* **Idempotent re-runs**: `--ci-from-env` (GitHub/GitLab) attaches a re-run of the same pull request
  to its live request; elsewhere a deterministic `--idempotency-key` does the same.
* **Never logged**: tokens (CI OIDC tokens, sessions), connection strings, row values. Output is ids,
  states, decision and reason codes.
* **Exit codes** (CLI): 24 denied by the profile, 25 still waiting for a human approval, 26 ended
  without READY, 27 timed out, 28 invalid manifest.

## Related

* [`examples/ci/`](../ci/README.md) — the earlier `run`/`lease` recipes using `datanivra_ci.py`
  (dataset id + target reference given by the pipeline). The recipes here use approved profiles
  instead, so the pipeline never chooses sources or targets.
* [Test Data API documentation](https://www.datanivra.com/docs/test-data-api) — administrator
  setup, workload identity, automatic approval and troubleshooting.
