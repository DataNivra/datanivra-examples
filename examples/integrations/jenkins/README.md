# Jenkins — illustrative

[`Jenkinsfile`](Jenkinsfile). Status: **illustrative, not run** (its CLI commands are parsed by the
real CLI parser in this repository's tests).

**Why a session token:** DataNivra workload identity trusts accept GitHub Actions and GitLab CI
tokens only, and DataNivra has no long-lived service credential. The pipeline therefore reads a
short-lived DataNivra session token from the Jenkins credential `datanivra-session-token`
(`withCredentials`), refreshed for the run by a process your security team approves. Jenkins masks
it in the console log; never `echo` it.

**Prerequisites:** agent labelled `datanivra-ci` reaching the profile's targets; the `datanivra`
CLI installed from PyPI (`pipx install datanivra-cli==0.1.0`); an approved profile.

**Every run:** request (`--idempotency-key` derived from `BUILD_TAG`, so a replayed stage gets the
same request) → wait → tests → `post { always { release } }` (success, failure, abort).

**Not provided:** unattended credentials. If you need them, ask for workload identity support for
your Jenkins OIDC setup (proposed, not implemented).
