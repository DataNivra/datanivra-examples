# Test Data API example gallery (synthetic)

Runnable and illustrative examples of the Universal Test Data API (ADR-0018): people, CI pipelines and QA
frameworks ask DataNivra for **approved** test data from versioned profiles, run *their own* tests against
the approved target, and release the data afterwards.

* **DataNivra provisions data; it does not run your tests.** Test frameworks (pytest, Playwright, JUnit, ...)
  execute tests. DataNivra prepares, certifies, leases and cleans up the data they use.
* **All data is synthetic.** Profiles here generate synthetic records from the industry packs (or lease a
  certified version of an estate you approved). No real patient, customer or employee data.
* **No credentials pass through DataNivra.** Requests return metadata (ids, states, checksums); your runner
  reaches the approved target with its own, separately managed access. Provisioning targets are
  PostgreSQL and directory targets only (`CONNECTOR_CAPABILITIES`).
* **Placeholder ids** in `profiles/*.yaml` look like `00000000-0000-4000-8000-0000000000NN`: replace them with
  your environment, dataset, agent and workload-identity ids.
* **Availability:** the CLI and SDKs are on PyPI and npm (`pipx install datanivra-cli`,
  `pip install datanivra-sdk`, `npm install @datanivra/sdk`). CI workload identity and automatic approval are off by default and need operator and tenant
  enablement (see the [automatic approval guide](https://www.datanivra.com/docs/automatic-approval)); without them, CI requests wait for a human approver.

## Status labels

| Label | Meaning |
| --- | --- |
| runnable in repo test | Executed by DataNivra's own test suite against the real control plane (embedded PostgreSQL, fake agent, fake CI issuer); the README's expected decision is asserted. |
| type-checked | TypeScript compiled with `tsc --noEmit -p examples/test-data-api/tsconfig.json` against the SDK sources; not executed against a server here. |
| illustrative | Shows the integration pattern; not compiled or executed in this repository (the language toolchain or framework is not a dependency here). |

## Profiles

| Profile | Fulfilment | Used by |
| --- | --- | --- |
| [`healthcare-integration`](profiles/healthcare-integration.yaml) | build (healthcare pack, synthetic) | 01, 18, 22 |
| [`banking-regression`](profiles/banking-regression.yaml) | build (financial-services pack) | 03, 11, 13 |
| [`insurance-claims`](profiles/insurance-claims.yaml) | build (insurance pack) | 04 |
| [`telecom-billing`](profiles/telecom-billing.yaml) | build (telecom pack) | 05 |
| [`manufacturing-traceability`](profiles/manufacturing-traceability.yaml) | build (manufacturing pack) | 06 |
| [`retail-orders`](profiles/retail-orders.yaml) | build (retail-ecommerce pack) | 02, 24 |
| [`edge-cases-core`](profiles/edge-cases-core.yaml) | build (core scenarios, no pack) | 07, 10, 14, 15, 16, 25 |
| [`orders-pr-regression`](profiles/orders-pr-regression.yaml) | lease a certified version (pool of 4) | 09, 17, 19, 21, 23 |
| [`warehouse-migration`](profiles/warehouse-migration.yaml) | lease a certified masked version | 08, 12, 20 |

## Scenarios

| id | title | industry | language | framework | CI | fulfilment | status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [01](scenarios/01-healthcare-postgresql/) | Healthcare integration on PostgreSQL | Healthcare | Python | pytest | any | `BUILD_DATASET` | runnable in repo test |
| [02](scenarios/02-ecommerce-refunds/) | E-commerce refunds and payment declines | Retail / e-commerce | TypeScript | Vitest | any | `BUILD_DATASET` | type-checked |
| [03](scenarios/03-banking-insufficient-funds/) | Banking: insufficient funds and duplicate payments | Banking | Python | pytest | any | `BUILD_DATASET` | runnable in repo test |
| [04](scenarios/04-insurance-claim-edge-cases/) | Insurance claim payout edge cases | Insurance | Java | JUnit 5 | any | `BUILD_DATASET` | illustrative |
| [05](scenarios/05-telecom-billing-disputes/) | Telecom billing disputes | Telecom | Go | go test | any | `BUILD_DATASET` | illustrative |
| [06](scenarios/06-manufacturing-lot-recall/) | Manufacturing lot recall traceability | Manufacturing | C# | NUnit | any | `BUILD_DATASET` | illustrative |
| [07](scenarios/07-saas-tenant-isolation/) | SaaS multi-tenant isolation regression | SaaS | TypeScript | Playwright | any | `BUILD_DATASET` | type-checked |
| [08](scenarios/08-warehouse-schema-migration/) | Warehouse schema migration rehearsal | Data warehouse | Bash | curl + jq | any | `LEASE_CERTIFIED_VERSION` | illustrative |
| [09](scenarios/09-postgresql-per-pr-lease/) | Per-PR PostgreSQL lease | Cross-industry | Python | pytest | GitHub Actions / GitLab CI | `LEASE_CERTIFIED_VERSION` | runnable in repo test |
| [10](scenarios/10-api-pagination-edge-cases/) | API pagination and malformed records | Cross-industry | JSON | Postman / Newman | any | `BUILD_DATASET` | illustrative |
| [11](scenarios/11-authz-cross-account/) | Authorization: cross-account access is refused | Cross-industry | Robot Framework | RequestsLibrary | any | `BUILD_DATASET` | illustrative |
| [12](scenarios/12-privacy-leakage-canary/) | Privacy: masked fields and leakage canaries | Privacy | Python | pytest | any | `LEASE_CERTIFIED_VERSION` | illustrative |
| [13](scenarios/13-financial-reconciliation/) | Financial reconciliation breaks | Banking | Python | pytest | any | `BUILD_DATASET` | illustrative |
| [14](scenarios/14-timezones-dst-leap-day/) | Time zones, DST and leap days | Cross-industry | TypeScript | Vitest (Jest-compatible API) | any | `BUILD_DATASET` | type-checked |
| [15](scenarios/15-unicode-localization/) | Unicode and localization | Cross-industry | TypeScript | Vitest | any | `BUILD_DATASET` | type-checked |
| [16](scenarios/16-performance-volume-ceiling/) | Performance volume with a hard ceiling | Cross-industry | Python | Locust | any | `BUILD_DATASET` | illustrative |
| [17](scenarios/17-chaos-runner-killed/) | Chaos: the runner is killed mid-test | Cross-industry | Python | pytest | any | `LEASE_CERTIFIED_VERSION` | illustrative |
| [18](scenarios/18-agent-bug-reproduction-pin/) | Agent-driven bug reproduction with a pinned request | Cross-industry | Python | pytest | any | `BUILD_DATASET` | runnable in repo test |
| [19](scenarios/19-parallel-pull-requests/) | Parallel pull requests share one certified version | Cross-industry | Bash | DataNivra CLI | GitHub Actions matrix | `LEASE_CERTIFIED_VERSION` | runnable in repo test |
| [20](scenarios/20-schema-evolution/) | Schema evolution across certified versions | Cross-industry | Python | pytest | any | `LEASE_CERTIFIED_VERSION` | illustrative |
| [21](scenarios/21-negative-permission-denied/) | Negative test: an unnamed identity is denied | Security | Python | pytest | any | `LEASE_CERTIFIED_VERSION` | runnable in repo test |
| [22](scenarios/22-auto-approval-vs-over-limit/) | Automatic approval vs over-limit requests | Healthcare | Python | pytest | GitHub Actions | `BUILD_DATASET` | runnable in repo test |
| [23](scenarios/23-ttl-expiry-teardown/) | Temporary access expires | Cross-industry | Bash | DataNivra CLI | any | `LEASE_CERTIFIED_VERSION` | illustrative |
| [24](scenarios/24-contract-testing-pact/) | Consumer/provider contract testing | Cross-industry | TypeScript | Pact | any | `BUILD_DATASET` | illustrative |
| [25](scenarios/25-developer-local-sandbox/) | Developer: approved data in a private sandbox | Cross-industry | Bash | DataNivra CLI | none (laptop) | `BUILD_DATASET` | illustrative |

## Validate, plan, run

```bash
datanivra test-data validate examples/test-data-api/profiles/healthcare-integration.yaml
datanivra test-data define examples/test-data-api/profiles/healthcare-integration.yaml --submit   # author
datanivra policies approve <POLICY_ID> 1 --expected-checksum <CHECKSUM> --reason "Reviewed"          # second person
datanivra test-data plan examples/test-data-api/scenarios/01-healthcare-postgresql/request.yaml
```
