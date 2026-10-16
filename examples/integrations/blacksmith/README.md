# GitHub Actions-compatible hosted runners (Blacksmith-style label) — illustrative

[`pr-test-data.yml`](pr-test-data.yml) is the GitHub Actions recipe with a different `runs-on`
label. Status: **illustrative, not run — GitHub Actions-compatible runner example, unverified.** The
workflow calls the same DataNivra CLI as any other runner.

What changes compared with a self-hosted runner: only the network. A hosted runner can use the
profile's data only if it can reach an approved target through private networking you set up
(and the profile's target pool points at targets reachable that way). DataNivra never sends data
to the runner; it hydrates the approved target from inside your network. Without such a path, use
a self-hosted runner.
