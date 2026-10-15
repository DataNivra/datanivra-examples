# Contributing

Thank you for helping improve this repository. It is maintained by DataNivra and contains
examples and templates for working with DataNivra. Please read this page before opening a pull
request.

## Before you start

- Read the [code of conduct](CODE_OF_CONDUCT.md) and the
  [synthetic data policy](SYNTHETIC_DATA_POLICY.md). **Only synthetic data** may be contributed.
- For anything larger than a small fix, open an issue first so we can agree on the approach.
- Security problems go through a private advisory ([SECURITY.md](SECURITY.md)), never a public
  issue or pull request.
- Contributions are accepted under the repository's licence ([LICENSE](LICENSE)). If the licence
  file says the licence is not yet decided, we cannot accept outside contributions yet; issues
  are still welcome.

## Pull requests

1. Keep a pull request focused on one change and explain _why_ in its description.
2. Never commit secrets, credentials, tokens, connection strings with passwords, private keys or
   `.env` files. Use references (`vault://...`, `k8s://...`, `env://...`) or `<PLACEHOLDER>` values.
3. Put new data files in a directory covered by a `SYNTHETIC_MANIFEST.json`.
4. Pin every third-party GitHub Action to a full commit SHA, with the version as a comment.
5. Make sure CI passes: secret scan, synthetic-data check and workflow lint.

A maintainer reviews every pull request. We may ask for changes, or decline a change that does
not fit the purpose of the repository.

## Releases

Releases follow [semantic versioning](https://semver.org). Each release is a signed, annotated
git tag `vMAJOR.MINOR.PATCH` with notes in [CHANGELOG.md](CHANGELOG.md). Breaking changes (a
renamed input, a removed example, a new minimum DataNivra version) only happen in a new major
version and are listed first in the changelog.
