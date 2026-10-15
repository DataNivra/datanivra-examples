# Self-hosted runners: network and access requirements

The test-data recipes need three network paths, and only three:

| From | To | Why |
| --- | --- | --- |
| runner | DataNivra control plane (https) | request / poll / release (metadata only) |
| runner | the approved target databases of the profile's pool | your tests read the provisioned copy |
| DataNivra agent (in your network) | the same targets | hydrate and tear down the copy |

The runner never needs access to your source systems, and DataNivra never needs inbound access to
the runner or the targets (the agent is outbound-only).

**Target credentials** belong to the runner, not to DataNivra: keep them in your CI secret store
(e.g. `APP_DB_DSN`) or have the runner fetch them from your vault. A test-data request returns an
`environment_id` (a reference), never a connection string or password.

**Isolation:** each live request holds one target of the profile's pool exclusively, so parallel
pull requests never share a copy. Size the pool for your parallelism; extra requests get
`TARGET_POOL_EXHAUSTED` (retry later) instead of sharing.

**Hardening:** run one job per runner (ephemeral runners preferred), restrict the runner's egress to
the paths above, and do not run fork pull requests on runners that can reach targets.
