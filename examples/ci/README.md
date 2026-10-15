# CI/CD with ephemeral, certified test data (reference integration)

Every build gets its own **certified, masked** dataset in an **ephemeral** environment.
The data is **destroyed** when the build finishes, and the run leaves an **evidence** record.
Rows never pass through CI or DataNivra Cloud: the agent inside your network builds,
certifies and provisions the data, and CI only orchestrates through the control-plane API.

| File | What it is |
| --- | --- |
| [`datanivra_ci.py`](datanivra_ci.py) | The pipeline script. It uses only the Python standard library. |
| [`github-actions/datanivra-test-data.yml`](github-actions/datanivra-test-data.yml) | A GitHub Actions workflow (`run` mode: a new dataset per build). Copy it to `.github/workflows/` in your repository. |
| [`github-actions/datanivra-ephemeral-pr.yml`](github-actions/datanivra-ephemeral-pr.yml) | A GitHub Actions pull-request workflow (`lease` mode): lease a certified version, test, release; release on PR close. |
| [`github-actions/datanivra-lease/action.yml`](github-actions/datanivra-lease/action.yml) | An optional composite action wrapping the lease modes. |
| [`dataset-request.template.json.tmpl`](dataset-request.template.json.tmpl) | A dataset request template. Fill it in and commit it as `ci/dataset-request.json`. |
| [`app_under_test/`](app_under_test) | A tiny "application under test" and its test suite. |

The whole flow (both modes, plus the PR-close clean-up) runs end to end, locally and
automatically, in DataNivra's own end-to-end test suite. That test uses real control-plane and agent processes,
embedded PostgreSQL and synthetic data only.

Two ways to get data for a test run:

* **`lease` mode (preferred for pull requests).** Lease an *already certified* dataset version
  into an ephemeral environment, run the tests, release the lease. No new dataset per run; the
  agent tears the leased copy down and confirms it. See [Lease mode](#lease-mode-pull-requests).
* **`run` mode.** Build, certify and provision a new dataset for each build, then revoke it.

## One-time set-up (TDM / platform team)

1. **Install an agent** in the network that holds the source systems and the CI target database.
   Register the sources, run discovery, and have the masking and certification policies **approved**.
   Approval needs a second person (separation of duties).
2. **Give the agent a CI target.** Store the connection document of the database or schema that
   receives ephemeral CI data in the *agent's* secret store. For example, an environment variable
   or a Kubernetes/Vault secret containing
   `{"kind": "POSTGRESQL", "host": ..., "dbname": ..., "user": ..., "password_ref": ..., "schema": "ci_ephemeral"}`.
   CI only ever sees the *reference* (`--target-ref`, e.g. `vault://tdm/ci-target`).
3. **Commit a request template** (`dataset-request.template.json.tmpl` → `ci/dataset-request.json`)
   with the source ids, the subset and the approved policy versions (`policy_id`, `version`,
   `checksum`). Leave out `target_environment_id`: the pipeline supplies it. Keep
   `retention_days` small (for example 1) as a backstop.
4. **Create a CI identity** with the roles `TDM_ENGINEER` (request, provision) and `DATA_ADMIN`
   (ephemeral environments, revoke). Store its bearer token as the CI secret
   `DATANIVRA_API_TOKEN`, and the API URL as `DATANIVRA_API_URL`.
5. **Use a runner that can reach the CI target database**, for example a self-hosted runner in that
   network. Your application tests connect to that database (for example with `APP_DB_DSN`).

## What a run does

```text
build trigger ─▶ ephemeral environment ─▶ request certified dataset ─▶ wait for job
     ─▶ verify CERTIFIED + manifest ─▶ pin (bookmark) ─▶ application tests ─▶ destroy (revoke) ─▶ evidence
```

| Step | API call (control plane `/v1`) | Notes |
| --- | --- | --- |
| Build trigger | none | The build id comes from `DATANIVRA_CI_BUILD_ID`, or from `GITHUB_RUN_ID` + `GITHUB_RUN_ATTEMPT`. |
| Ephemeral target | `POST /v1/environments` with `{"ephemeral": true, "expires_at": now+TTL, "target_ref": ...}` | The control plane refuses to provision into an expired environment. |
| Request | `POST /v1/dataset-requests` with `Idempotency-Key: ci-<build id>` | A CI retry returns the same dataset. |
| Wait | `GET /v1/jobs?dataset_id=<id>` | Polls with bounded backoff (1 s → 10 s) and stops at `--timeout`. |
| Verify | `GET /v1/certification-reports?dataset_id=<id>`, `GET /v1/datasets/<id>/versions/1/manifest` | The report must be `CERTIFIED`, every gate must pass, and the checksums must match. Otherwise no tests run. |
| Provision | done by the agent as the last step of the certified build | `provision-pin` uses `POST /v1/datasets/<id>/versions/<v>/provision`. |
| Bookmark | none; `--pin-out pin.json` | Records the dataset id, version, manifest checksum, certification report id, engine version and packs. |
| Tests | `--test-command` | Receives `DATANIVRA_CI_DATASET_ID`, `DATANIVRA_CI_DATASET_VERSION` and `DATANIVRA_CI_MANIFEST_CHECKSUM`. The API token is removed from its environment. |
| Destroy | `POST /v1/datasets/<id>/revoke` with `{"reason_code": "CI_PIPELINE_COMPLETE"}`, then wait for the `REVOKE_DATASET` jobs | The agent deletes its local copy and deprovisions **every** target it loaded. |
| Evidence | none; `--evidence evidence.json` | One JSON record per step, holding ids, states, timings, checksums and the exit code. It contains no rows and no secrets. |

**Exit codes.**

* `0`: the tests passed.
* `1`: the tests failed.
* `2`: pipeline error, for example no certified data, a timeout or an API error.

Destroy runs in every case unless you pass `--keep`. With `--keep-on-failure`, a failed build's
data is kept so you can debug it.

## Lease mode (pull requests)

```text
CI context ─▶ request lease ─▶ hydrate (agent) ─▶ READY ─▶ application tests
     ─▶ release (always) ─▶ teardown confirmed ─▶ lease evidence (digest verified)
pull_request closed ─▶ lease-cleanup: release every live lease of that PR
```

```bash
python examples/ci/datanivra_ci.py lease --dataset-id "$DATASET_ID" \
  --agent-id "$AGENT_ID" --target-ref "$TARGET_REF" --tier QA --ttl-minutes 60 \
  --test-command "python -m pytest -q tests" \
  --evidence lease-steps.json --lease-evidence-out lease-evidence.json
python examples/ci/datanivra_ci.py lease-cleanup --this-run   # `if: always()` backstop
python examples/ci/datanivra_ci.py lease-cleanup              # on `pull_request: closed`
```

| Step | API call | Notes |
| --- | --- | --- |
| CI context | none | A provider-neutral adapter reads repository, PR/MR number, run id + attempt and commit SHA (GitHub Actions first, GitLab CI second). Never branch names, titles, authors or tokens. |
| Request | `POST /v1/environment-leases` with `ci_ref` and `Idempotency-Key: ci-<sha256>` | The key covers repository + PR + run + attempt + SHA + the request, so a retried step or a duplicated webhook delivery replays the same lease. A re-run of the same commit gets the still-live lease back (control-plane de-duplication); a new attempt after a release gets a new lease. |
| Wait / hydrate | `GET /v1/environment-leases/<id>` | Until READY. `LEASE_ENDED` (FAILED/EXPIRED/…) or `LEASE_TIMEOUT` fails the run with exit 2. |
| Tests | `--test-command` | Receives `DATANIVRA_CI_LEASE_ID`, `DATANIVRA_CI_DATASET_ID`, `DATANIVRA_CI_DATASET_VERSION`, `DATANIVRA_CI_ENVIRONMENT_ID`; never the API token. |
| Release | `POST /v1/environment-leases/<id>/release`, then poll | Runs in every case (unless `--keep-on-failure` after failing tests; the lease then lapses at its TTL or is released on PR close). Done only when the agent confirmed the teardown (`cleanup_confirmed_at`). |
| Evidence | `GET /v1/environment-leases/<id>/evidence` | The value-free record (state events, certificate id + digest, hydrate/teardown receipts, timings, CI reference). Its SHA-256 digest is recomputed over the canonical JSON; a mismatch is `LEASE_EVIDENCE_DIGEST_MISMATCH` (exit 2). |

The CI identity needs `dataset.provision` and, to create the lease's environment from a target
reference, `environment.manage` (for example `TDM_ENGINEER` + `DATA_ADMIN`). The same flow with
the `datanivra` CLI: `env-leases create --ci-from-env --wait` (derives the same kind of
idempotency key), `env-leases release`, `env-leases evidence` and, on PR close,
`env-leases release-ci --ci-from-env`.

**`destroy` vs lease release.** `destroy` revokes the whole dataset version for everyone and
deprovisions every target it was loaded into; it stays for `run` mode and pinned reproductions.
For per-run clean-up of a leased environment, release the lease instead: it removes only that
environment's copy and leaves the certified version usable by other runs.

### Reproducing a failure from its pin

```bash
# Provision exactly the certified version that the failed build used, into a new ephemeral environment:
python examples/ci/datanivra_ci.py provision-pin datanivra-pin.json \
  --agent-id "$AGENT_ID" --target-ref "$TARGET_REF" --tier QA --evidence repro.json
# When done, destroy it. This deprovisions every environment the version was loaded into:
python examples/ci/datanivra_ci.py destroy datanivra-pin.json --evidence destroy.json
```

`provision-pin` re-verifies the certification and refuses the run if the manifest checksum no
longer matches the pin. A revoked version cannot be provisioned: the API answers 409
`DATASET_NOT_PROVISIONABLE`.

## Using the API directly (curl)

```bash
H="Authorization: Bearer $DATANIVRA_API_TOKEN"
curl -sf -X POST "$DATANIVRA_API_URL/v1/environments" -H "$H" -H 'Content-Type: application/json' \
  -d '{"name":"ci-1234","tier":"QA","agent_id":"<agent>","target_ref":"vault://tdm/ci-target","ephemeral":true,"expires_at":"2026-01-01T12:00:00Z"}'
curl -sf -X POST "$DATANIVRA_API_URL/v1/dataset-requests" -H "$H" -H 'Idempotency-Key: ci-1234' \
  -H 'Content-Type: application/json' -d @ci/dataset-request.json   # with target_environment_id added
curl -sf "$DATANIVRA_API_URL/v1/jobs?dataset_id=<dataset>" -H "$H"
curl -sf "$DATANIVRA_API_URL/v1/certification-reports?dataset_id=<dataset>" -H "$H"
curl -sf -X POST "$DATANIVRA_API_URL/v1/datasets/<dataset>/revoke" -H "$H" -H 'Content-Type: application/json' \
  -d '{"reason_code":"CI_PIPELINE_COMPLETE"}'
```

## SDK and CLI equivalents

The typed TypeScript SDK (`@datanivra/sdk`) exposes these same REST operations. The Python SDK
and the `datanivra` command-line tool wrap the same operations: `createEnvironment`, `createDatasetRequest`, `listJobs`,
`listCertificationReports`, `getDatasetManifest`, `provisionDataset` and `revokeDataset` (the
operation ids in `packages/contracts`). A CLI version of this pipeline makes the same calls in
the same order: create an ephemeral environment, request, wait, verify, then revoke. This
reference uses plain HTTP so that it runs on any runner without installing anything. Behaviour
is identical whichever client you use, because every rule (approved policies, certification,
tenant isolation, audit) is enforced by the control plane and the agent, not by the client.

## Guarantees and limits

* The pipeline never receives rows or source credentials. The evidence file holds only metadata.
* Tests run only against a version whose certification report is `CERTIFIED` with every gate passed.
* Lease mode: the lease TTL (and the absolute lifetime) is the backstop when a runner dies before
  the release; the control-plane sweep expires the lease and orders the same teardown.
* When the pipeline is killed before destroy, the data is removed by retention expiry
  (`retention_days`, via the control-plane scheduler) or by a later `destroy` run. After the
  environment's `expires_at`, the environment cannot receive any new data.
* Environment expiry alone does **not** delete data that was already provisioned. Revoke (or
  retention) does.
