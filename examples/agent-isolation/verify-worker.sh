#!/usr/bin/env bash
# Show the hardening of every running DataNivra worker container on this host (run while a job runs).
# Expected: ReadonlyRootfs=true, CapDrop=[ALL], no-new-privileges, Privileged=false, LogConfig=none,
# NetworkMode=none (or your source/target network) and no runtime socket among the mounts.
set -euo pipefail
cli="${DATANIVRA_AGENT_ISOLATION_RUNTIME_CLI:-docker}"
names=$("$cli" ps --filter label=io.datanivra.isolation=worker --format '{{.Names}}')
if [ -z "$names" ]; then
  echo "no worker is running right now (start a job, then run this again)"; exit 0
fi
for name in $names; do
  "$cli" inspect --format \
    '{{.Name}} stage={{index .Config.Labels "io.datanivra.stage"}} readonly={{.HostConfig.ReadonlyRootfs}} capdrop={{.HostConfig.CapDrop}} secopt={{.HostConfig.SecurityOpt}} privileged={{.HostConfig.Privileged}} network={{.HostConfig.NetworkMode}} logs={{.HostConfig.LogConfig.Type}} user={{.Config.User}}' \
    "$name"
  if "$cli" inspect --format '{{range .Mounts}}{{.Source}} {{end}}' "$name" | grep -q 'docker.sock\|podman.sock\|containerd.sock'; then
    echo "  WARNING: a runtime socket is mounted into $name"; exit 1
  fi
done
