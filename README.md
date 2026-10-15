<img src="https://www.datanivra.com/brand/datanivra-logo-on-light.svg" alt="DataNivra logo" width="240">

# DataNivra examples

**Realistic test data. Production data stays home.**

DataNivra is a test data management (TDM) platform. A DataNivra agent runs **inside your network**
and builds, masks, subsets and certifies test data there; the DataNivra control plane only
coordinates (ids, states, policies, checksums). Rows never leave your environment: zero
raw-production-data egress, customer-resident processing.

This repository holds DataNivra's public, copyable examples: how people, CI pipelines, QA
frameworks and AI agents ask for **approved** test data, run *their own* tests against it, and
release it afterwards. Everything here uses **synthetic data only**. The DataNivra product itself
(control plane, agent, engine) is not open source; these examples call its public CLI, SDKs and
REST API.

Browse the same examples, rendered, at **https://www.datanivra.com/examples**.

## What is in here

| Path | What it is |
| --- | --- |
| [`examples/test-data-api/`](examples/test-data-api) | The Test Data API gallery: **25 scenarios** (healthcare, banking, insurance, telecom, manufacturing, retail, SaaS, data warehouse; pytest, Vitest, Playwright, JUnit, NUnit, go test, Robot Framework, Postman, Locust, Pact, curl, the CLI) and the **9 test data profiles** they use. Each scenario has a README (why, what is requested, policy gates, expected decision, cleanup), a `request.yaml` and code. Start with [`examples/test-data-api/README.md`](examples/test-data-api/README.md). |
| [`examples/integrations/`](examples/integrations) | CI/CD recipes: GitHub Actions and GitLab CI with workload identity (OIDC, no stored DataNivra secret), Jenkins, Azure DevOps, CircleCI, a generic shell/Python runner, self-hosted runners and ephemeral Kubernetes targets. Every recipe does *request → wait → test → always release*. |
| [`examples/mcp/`](examples/mcp) | A local, stdio-only Model Context Protocol adapter example: an AI agent can list permitted profiles, validate, plan, request, poll and release — and nothing else (no approvals, no rows, no secrets). |
| [`examples/ci/`](examples/ci) | The earlier dataset-centric CI recipes: a standard-library pipeline script with `run` (build + certify per build) and `lease` (lease a certified version per pull request) modes. |

## How it works

1. **A profile says what may be requested.** A tenant administrator defines a test data profile
   (scenarios, maximum counts, targets, time to live, and which CI identities may get data
   automatically); a second person approves it. Profiles are versioned and immutable.
2. **A request asks for data within the profile.** People, pipelines or agents send a small
   manifest (`request.yaml`). DataNivra decides: `AUTO_APPROVED` (inside an envelope a second
   person approved, where automatic approval is enabled), `PENDING_HUMAN_APPROVAL`, or `DENIED`
   (outside the profile). The decision and its reason codes are returned; nothing else.
3. **Your agent provisions it inside your network.** It builds a synthetic dataset, or leases a
   DataNivra-certified version into an isolated target from the profile's pool.
4. **Your tests run, with your own access.** DataNivra never returns target credentials; your
   runner reaches the approved target with its own, separately managed access.
5. **Release, always.** Releasing (or the lease's time to live expiring) tears the copy down; a
   value-free evidence record (ids, states, checksums) is kept.

## Try it

```bash
datanivra test-data validate examples/test-data-api/profiles/healthcare-integration.yaml
datanivra test-data plan examples/test-data-api/scenarios/01-healthcare-postgresql/request.yaml
```

You need a DataNivra tenant and a customer-resident agent; start a free trial at
https://www.datanivra.com. The DataNivra CLI and SDKs are provided with your DataNivra release
(installation: https://www.datanivra.com/docs/test-data-sdk-helpers). No account yet? The
synthetic playground at https://www.datanivra.com/demo runs the workflow in your browser.

## Compatibility

| Component | Version these examples were written for |
| --- | --- |
| Control-plane API | `v1` |
| Agent | `0.4.4` |

## Documentation

* Test Data API: https://www.datanivra.com/docs/test-data-api
* Test data profiles: https://www.datanivra.com/docs/test-data-profiles
* Workload identity for CI: https://www.datanivra.com/docs/workload-identity
* Automatic approval: https://www.datanivra.com/docs/automatic-approval
* CI recipes: https://www.datanivra.com/docs/test-data-ci-recipes
* Troubleshooting: https://www.datanivra.com/docs/test-data-troubleshooting

## Licence, support and security

The examples in this repository are MIT-licensed ([LICENSE](LICENSE)); DataNivra itself is
commercial software under its own terms (https://www.datanivra.com/legal). Support boundary:
[SUPPORT.md](SUPPORT.md). Report security issues privately: [SECURITY.md](SECURITY.md). Data
policy for contributions: [SYNTHETIC_DATA_POLICY.md](SYNTHETIC_DATA_POLICY.md).
