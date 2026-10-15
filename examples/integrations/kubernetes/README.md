# Ephemeral Kubernetes targets (per-run namespace + database)

Guidance, not a separate integration: the CI recipes stay the same; what changes is the target pool.

1. Pre-create N per-run target slots with the self-hosted ephemeral PostgreSQL target that ships
   with the agent's deployment examples ([agent installation](https://www.datanivra.com/docs/agent-installation)):
   one namespace per slot, restricted Pod Security, default-deny NetworkPolicy, one PostgreSQL each.
2. Register each slot's connection settings in your secret provider and list the references in the
   profile's `lease.target_pool` (for example `vault://ci/k8s-slot-1` … `vault://ci/k8s-slot-8`).
   The profile is approved by a second person; a pipeline can never add a slot.
3. Allow the CI runner (and the DataNivra agent) to reach those namespaces only.

Every request then gets one free slot; release (or TTL expiry) makes the agent tear the copy down,
and the slot returns to the pool. DataNivra does not create namespaces or clone databases itself
(no native clone: ADR-0016); per-lease isolation comes from the separate slots.
