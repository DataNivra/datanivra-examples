# CircleCI — illustrative

[`config.yml`](config.yml). Status: **illustrative, not run** (YAML parsed, CLI commands parsed by
the real CLI parser).

**Auth:** CircleCI OIDC is not supported by DataNivra trusts yet, and there is no long-lived
DataNivra service credential: the job expects a short-lived session token as `DATANIVRA_TOKEN` in
the context `datanivra`.

**Network:** CircleCI cloud machines normally cannot reach databases inside your network; the
example uses a self-hosted runner resource class (`acme/datanivra-ci`).

**Every run:** request (idempotency key from the workflow id and build number) → wait → tests →
release in a `when: always` step.
