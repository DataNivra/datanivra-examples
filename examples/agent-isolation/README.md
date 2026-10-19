# Isolated execution for the DataNivra agent

**Status:** Preview · **Where it runs:** your agent host (Linux) · **Needs:** Docker ≥ 24 or Podman ≥ 4 (gVisor: `runsc`; Firecracker: KVM)

Run every row-level stage of your agent's jobs — profiling, classification, subsetting, masking, synthesis, validation and provisioning — in a fresh, hardened, short-lived container instead of the agent process. Each worker sees only its stage's input and output, this job's own connection details and the keys this job's masking policy names: never the agent's identity key, its control-plane token, your secret store, the container runtime or other jobs. Published data is byte-for-byte the same as without isolation.

Full guide: [Isolated execution](https://www.datanivra.com/docs/isolated-execution).

## 1. Configure the agent

Copy [`agent.isolation.env.example`](agent.isolation.env.example) into your agent's environment and fill in the image digest of your agent release (see [Packages and downloads](https://www.datanivra.com/docs/packages-and-downloads)). Run the agent as an unprivileged user that may use a **rootless** Docker or Podman.

## 2. Give network stages a narrow network (optional)

Stages that read a network source or write a network target join an operator network; every other stage runs with no network at all. [`create-worker-networks.sh`](create-worker-networks.sh) creates the two networks and prints the firewall rules (for you to review and apply) that let them reach only the systems you name — nothing else on the network, nothing on the Docker host itself, and DNS only through the resolvers you list:

```bash
./create-worker-networks.sh --source 10.20.0.15:5432 --target 10.30.0.8:5432 --resolver 10.0.0.2
```

Prefer an internal resolver that answers only for your own zones, or use IP addresses in connection documents and omit `--resolver`.

## 3. Check the host

```bash
datanivra-agent isolation doctor        # every check must pass
./verify-worker.sh                      # while a job runs: shows each worker's hardening
```

## 4. Require it for your organization

An organization admin sets the minimum (console **Organization → Execution isolation**, or `datanivra org isolation-update --min-isolation CONTAINER`). Jobs then go only to agents that meet it, and requests can ask for more isolation, never less:

```bash
datanivra test-data request --profile-ref healthcare-integration@1 --min-isolation KERNEL_BOUNDARY --isolation-backend GVISOR
```

No data is included in this example: it configures and checks the agent host only.
