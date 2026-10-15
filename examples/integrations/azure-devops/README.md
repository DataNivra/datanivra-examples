# Azure DevOps — illustrative

[`azure-pipelines.yml`](azure-pipelines.yml). Status: **illustrative, not run** (YAML parsed, CLI
commands parsed by the real CLI parser).

**Auth:** Azure DevOps workload identity federation is not supported by DataNivra trusts yet, and
there is no long-lived DataNivra service credential. The pipeline expects a short-lived session
token in the secret variable `DATANIVRA_TOKEN` (variable group `datanivra`), passed to steps through
`env:` only (secret variables are not exposed to scripts otherwise and are masked in logs).

**Prerequisites:** self-hosted agent pool `datanivra-ci` reaching the profile's targets; the CLI
(`datanivra-cli` from PyPI, installed by the pipeline); an approved profile.

**Every run:** request (idempotency key from `Build.BuildId` + `System.JobAttempt`) → wait → tests →
release with `condition: always()` (success, failure, cancellation).
