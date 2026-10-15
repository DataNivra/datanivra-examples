# Security policy

## Reporting a vulnerability

Please report suspected vulnerabilities **privately** through a GitHub private security advisory
on this repository ("Security" tab, then "Report a vulnerability"). Do not open a public issue,
pull request or discussion for a security report, and do not include real personal data,
credentials or production records in a report.

We acknowledge reports as soon as we can and keep you informed while we investigate. Please give
us a reasonable time to fix a confirmed issue before you disclose it. This repository has no bug
bounty programme.

## Scope

This repository contains examples and templates that use **synthetic data only**. In scope:

- a secret, credential or real-looking personal record committed to this repository;
- an example that, if copied as documented, would weaken a deployment (for example by disabling
  TLS, granting write access to a source system or exposing a secret value);
- a GitHub Action or workflow in this repository that could be abused (script injection,
  unpinned third-party code, excessive token permissions).

Vulnerabilities in the DataNivra service, agent or website are also welcome through the same
private channel; they are triaged by DataNivra's security process.

## Supported versions

Only the latest release (or the default branch, before the first release) receives fixes.
