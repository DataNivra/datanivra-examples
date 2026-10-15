#!/usr/bin/env python3
"""Reference CI/CD integration: certified, ephemeral test data for every build.

This script needs only the Python standard library, so a CI runner can use it with nothing
installed. It talks to the DataNivra control-plane REST API (``/v1``) using a bearer token.
Rows never pass through CI: the customer-resident agent builds, certifies and provisions the
data inside your network, and this script only orchestrates and records *metadata*.

Pipeline (``run``)
------------------
1. **build trigger** — the build id comes from ``DATANIVRA_CI_BUILD_ID``, from GitHub Actions
   (``GITHUB_RUN_ID`` + ``GITHUB_RUN_ATTEMPT``), or is generated locally.
2. **ephemeral target** — ``POST /v1/environments`` with ``ephemeral=true`` and ``expires_at``
   set to now + ``--ttl-hours``. After that time the control plane refuses any further
   provisioning into the environment.
3. **request a certified dataset** — ``POST /v1/dataset-requests`` from a reviewed request template
   (sources, subset, *approved* policy versions). The ephemeral environment is the target, and
   the Idempotency-Key is the build id, so a CI retry never creates a second dataset. When the
   tenant requires approval for the request (production sources by default), the pipeline waits
   (``--timeout``) until a person with ``dataset.approve`` approves it; a rejection fails the
   build (``REQUEST_REJECTED``).
4. **wait for the job** — poll ``GET /v1/jobs?dataset_id=...`` with bounded backoff until it is
   terminal or ``--timeout`` elapses.
5. **verify certification** — ``GET /v1/certification-reports`` must be ``CERTIFIED`` with every
   gate passed, and the manifest checksum must match. Tests never run against uncertified data.
   The agent provisions the certified version into the ephemeral target as the last step of the
   build.
6. **bookmark the test state** — write a *pin* (``--pin-out``): dataset id, version, manifest
   checksum, certification report id, engine version and packs. The pin identifies exactly which
   certified data the tests ran against. ``provision-pin`` re-provisions it into a new ephemeral
   environment to reproduce a failure, as long as the version has not been destroyed.
7. **run the application tests** — ``--test-command`` runs in a subprocess, with this process's
   environment plus ``DATANIVRA_CI_DATASET_ID`` / ``DATANIVRA_CI_DATASET_VERSION``.
8. **destroy / expire** — ``POST /v1/datasets/{id}/revoke`` with ``CI_PIPELINE_COMPLETE``. The agent
   deletes its local publication and deprovisions every target it loaded. The script waits for
   the revoke job(s) to succeed. ``--keep-on-failure`` keeps a failed build's data for
   debugging. Retention (``retention_days`` in the template) and the environment expiry are the
   backstop if the pipeline is killed before this step.
9. **evidence** — ``--evidence`` receives a JSON record of every step (ids, states, timings,
   checksums, test exit code). Store it as a CI artifact.

Lease mode (``lease``, Workbook 06 EE-03/EE-13) — preferred for pull requests
------------------------------------------------------------------------------
For a dataset version that is *already certified* (e.g. built nightly), a test run does not need
its own dataset: it leases the certified version into an ephemeral environment and releases it.

1. **CI context** — a provider-neutral adapter (GitHub Actions first, GitLab CI second; the same
   rules as ``datanivra_cli.ci_context``) reads repository, PR/MR number, run id + attempt and
   commit SHA from the job environment. Nothing else (branch names, titles, authors, tokens).
2. **request** — ``POST /v1/environment-leases`` with that ``ci_ref`` and a deterministic
   Idempotency-Key over repository + PR + run + attempt + SHA + request, so a retried step or a
   duplicated webhook delivery replays the same lease; a CI *re-run* of the same commit gets the
   still-live lease back (control-plane de-duplication).
3. **wait** — poll until READY; FAILED/EXPIRED/RELEASED/ORPHANED (``LEASE_ENDED``) or the timeout
   (``LEASE_TIMEOUT``) fail the pipeline.
4. **test** — ``--test-command`` runs with ``DATANIVRA_CI_LEASE_ID``, ``DATANIVRA_CI_DATASET_ID``,
   ``DATANIVRA_CI_DATASET_VERSION`` and ``DATANIVRA_CI_ENVIRONMENT_ID`` (no API token).
5. **release** — ``POST .../release`` (idempotent), then wait until the agent confirmed the
   teardown (``cleanup_confirmed_at``). ``--keep-on-failure`` leaves a failed run's lease live
   until its TTL lapses.
6. **evidence** — ``GET .../evidence`` (value-free record); its SHA-256 digest is recomputed over
   the canonical JSON and must match (``LEASE_EVIDENCE_DIGEST_MISMATCH`` otherwise).
   ``--lease-evidence-out`` stores the record; ``--evidence`` gets the step log (metadata only).

``lease-cleanup`` releases every live lease of one pull request (run it on ``pull_request:
closed``); releasing is idempotent, so it is safe when the PR run already released its lease.

Other commands: ``provision-pin PIN`` (provision a pinned certified version into a new ephemeral
environment) and ``destroy PIN`` (revoke a pinned dataset). ``destroy`` revokes the whole dataset
version for everyone; for per-run clean-up of a leased environment prefer the lease release.

Configuration: ``DATANIVRA_API_URL`` (e.g. ``https://api.example.invalid``) and
``DATANIVRA_API_TOKEN``, a bearer token for a CI identity holding the dataset request, provision
and revoke permissions. Store both as CI secrets and never print them. The target reference
(``--target-ref``) is resolved by the agent from *its* secret store, so CI never holds database
credentials for the source.

Exit codes: 0 = tests passed; 1 = tests failed; 2 = pipeline error (no certified data,
timeout, API error). Destroy runs in every case unless ``--keep`` is given.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import re
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

TERMINAL = {"SUCCEEDED", "FAILED", "CANCELLED"}
LEASE_WAITING = {"REQUESTED", "HYDRATING"}
LEASE_LIVE = {"REQUESTED", "HYDRATING", "READY"}
LEASE_ENDED = {"RELEASED", "EXPIRED", "FAILED", "ORPHANED"}


class PipelineError(Exception):
    """A step failed; ``code`` is a stable machine code recorded in the evidence."""

    def __init__(self, code: str, detail: str = "") -> None:
        """``code`` is the stable machine code; ``detail`` is optional context (never secrets)."""
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code


def _secure_api_url(base_url: str) -> bool:
    """https, or http to a loopback host only (ENG-047): the bearer token must not travel in clear.

    The host is parsed, not prefix-matched, so ``http://localhost.attacker.example`` is refused.
    """
    parts = urllib.parse.urlsplit(base_url)
    host = (parts.hostname or "").rstrip(".")
    if parts.scheme == "https" and host:
        return True
    if parts.scheme != "http":
        return False
    if host == "localhost" or host.endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Never follow a redirect (WB13 MV-15).

    ``urllib`` follows 3xx by default and copies the ``Authorization`` header to the new location,
    whatever its host or scheme: one redirect from a proxy or a mis-configured API URL would send
    the CI bearer token to that host (e.g. a cloud metadata address, or over plain http). The API
    never redirects, so a 3xx is an error (``API_REDIRECT_REFUSED``).
    """

    def redirect_request(self, *_args: Any, **_kwargs: Any) -> None:
        """Returning ``None`` makes urllib raise the 3xx as an ``HTTPError``."""
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


class Client:
    """Minimal JSON client for the DataNivra REST API (bearer token, bounded timeouts, no redirects)."""

    def __init__(self, base_url: str, token: str, timeout: float = 30.0) -> None:
        """Refuse insecure API URLs up front so the bearer token is never sent in clear text."""
        if not _secure_api_url(base_url):
            raise PipelineError("INSECURE_API_URL", "use https (http only for a local control plane)")
        self.base = base_url.rstrip("/")
        self._token = token
        self.timeout = timeout

    def call(self, method: str, path: str, body: Any = None, *, idempotency_key: str | None = None) -> Any:
        """Send one authenticated JSON request and return the decoded response body.

        ``idempotency_key`` makes retried POSTs safe. HTTP errors become PipelineError with the API's
        error ``code``; network errors and timeouts become ``API_UNREACHABLE``.
        """
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method)  # noqa: S310 (https / local)
        req.add_header("Authorization", f"Bearer {self._token}")
        req.add_header("Accept", "application/json")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        if idempotency_key:
            req.add_header("Idempotency-Key", idempotency_key)
        try:
            with _OPENER.open(req, timeout=self.timeout) as resp:
                return json.loads(resp.read() or b"null")
        except urllib.error.HTTPError as err:
            if 300 <= err.code < 400:  # never follow: the token must not travel to another location
                raise PipelineError("API_REDIRECT_REFUSED", f"{method} {path} -> {err.code}") from None
            try:
                code = str(json.loads(err.read()).get("code", f"HTTP_{err.code}"))
            except ValueError:
                code = f"HTTP_{err.code}"
            raise PipelineError(code, f"{method} {path} -> {err.code}") from None
        except (urllib.error.URLError, TimeoutError) as err:
            raise PipelineError("API_UNREACHABLE", f"{method} {path}: {type(err).__name__}") from None

    def items(self, path: str) -> list[dict[str, Any]]:
        """Every item of a cursor-paginated list endpoint."""
        out: list[dict[str, Any]] = []
        cursor: str | None = None
        sep = "&" if "?" in path else "?"
        for _ in range(1000):
            page = self.call("GET", f"{path}{sep}limit=200" + (f"&cursor={cursor}" if cursor else ""))
            out.extend(page["items"])
            cursor = page.get("page", {}).get("next_cursor")
            if not cursor:
                return out
        raise PipelineError("PAGINATION_RUNAWAY", path)


class Evidence:
    """Step-by-step pipeline record (metadata only), written as JSON."""

    def __init__(self, path: Path | None, build_id: str) -> None:
        """Start a record for ``build_id``; ``path`` None keeps the record in memory only."""
        self.path = path
        self.doc: dict[str, Any] = {
            "build_id": build_id,
            "started_at": _now().isoformat(),
            "steps": [],
            "result": "RUNNING",
        }

    def step(self, name: str, **fields: Any) -> None:
        """Append a timestamped step, print it as one log line and rewrite the evidence file."""
        self.doc["steps"].append({"step": name, "at": _now().isoformat(), **fields})
        print(f"[datanivra-ci] {name}: " + json.dumps(fields, sort_keys=True, default=str), flush=True)  # noqa: T201
        self.write()

    def finish(self, result: str, **fields: Any) -> None:
        """Record the final result and finish time, then rewrite the evidence file."""
        self.doc.update(result=result, finished_at=_now().isoformat(), **fields)
        self.write()

    def write(self) -> None:
        """Write the record as sorted, indented JSON (no-op when no path was given)."""
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.doc, indent=2, sort_keys=True, default=str) + "\n", "utf-8")


def _now() -> datetime:
    """Current time in UTC (timezone-aware)."""
    return datetime.now(UTC)


def build_id_from_env() -> str:
    """Identify this pipeline run: ``DATANIVRA_CI_BUILD_ID``, else the GitHub run id and attempt, else
    random.

    The build id also forms the request's idempotency key, so a retried run reuses its request.
    """
    explicit = os.environ.get("DATANIVRA_CI_BUILD_ID")
    if explicit:
        return explicit
    run = os.environ.get("GITHUB_RUN_ID")
    if run:
        return f"gh-{run}-{os.environ.get('GITHUB_RUN_ATTEMPT', '1')}"
    return f"local-{uuid.uuid4().hex[:12]}"


# --------------------------------------------------------------------------- CI trigger adapters
# Stdlib copy of ``datanivra_cli.ci_context`` (this script must run on a bare CI runner).
# A contract test in DataNivra's own test suite keeps both implementations in step.

_RUN_ID = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")
_REPOSITORY = re.compile(r"^[A-Za-z0-9._-]{1,100}(/[A-Za-z0-9._-]{1,100}){1,3}$")
_COMMIT = re.compile(r"^[a-f0-9]{7,64}$")


@dataclass(frozen=True)
class CiContext:
    """Identifiers of one CI job attempt (no names, titles, authors or tokens)."""

    provider: str
    repository: str
    pr_number: int | None = None
    run_id: str | None = None
    run_attempt: str | None = None
    commit_sha: str | None = None

    def ci_ref(self) -> dict[str, Any]:
        """The lease ``CiRef`` (attempt excluded: the control plane de-duplicates re-runs)."""
        ref: dict[str, Any] = {"provider": self.provider, "repository": self.repository}
        for key in ("pr_number", "run_id", "commit_sha"):
            if getattr(self, key) is not None:
                ref[key] = getattr(self, key)
        return ref

    def idempotency_key(self, *discriminators: str) -> str:
        """``ci-`` + 60 hex of SHA-256 over repo, PR, run, attempt, SHA and ``discriminators``."""
        material = json.dumps(
            [
                self.provider,
                self.repository.lower(),
                self.pr_number,
                self.run_id,
                self.run_attempt,
                self.commit_sha,
                *discriminators,
            ],
            separators=(",", ":"),
        )
        return "ci-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:60]


def _digits(value: str | None) -> int | None:
    """A positive integer from a CI variable, else ``None``."""
    return int(value) if value and value.isdigit() and int(value) >= 1 else None


def _matching(value: str | None, pattern: re.Pattern[str]) -> str | None:
    """``value`` when it matches the contract pattern, else ``None`` (never sent malformed)."""
    return value if value and pattern.match(value) else None


def ci_context_from_env(env: dict[str, str] | None = None) -> CiContext | None:
    """GitHub Actions first, GitLab CI second; ``None`` elsewhere or for an invalid repository."""
    env = dict(os.environ) if env is None else env
    ctx: CiContext | None = None
    if env.get("GITHUB_ACTIONS") == "true" and env.get("GITHUB_REPOSITORY"):
        ref = env.get("GITHUB_REF", "")
        parts = ref.split("/")
        ctx = CiContext(
            provider="GITHUB_ACTIONS",
            repository=env["GITHUB_REPOSITORY"],
            pr_number=_digits(parts[2]) if ref.startswith("refs/pull/") and len(parts) > 2 else None,
            run_id=_matching(env.get("GITHUB_RUN_ID"), _RUN_ID),
            run_attempt=_matching(env.get("GITHUB_RUN_ATTEMPT"), _RUN_ID),
            commit_sha=_matching(env.get("GITHUB_SHA", "").lower(), _COMMIT),
        )
    elif env.get("GITLAB_CI") == "true" and env.get("CI_PROJECT_PATH"):
        ctx = CiContext(
            provider="GITLAB_CI",
            repository=env["CI_PROJECT_PATH"],
            pr_number=_digits(env.get("CI_MERGE_REQUEST_IID")),
            run_id=_matching(env.get("CI_PIPELINE_ID"), _RUN_ID),
            run_attempt=_matching(env.get("CI_JOB_ID"), _RUN_ID),
            commit_sha=_matching(env.get("CI_COMMIT_SHA", "").lower(), _COMMIT),
        )
    return ctx if ctx is not None and _REPOSITORY.match(ctx.repository) else None


def canonical_digest(record: dict[str, Any]) -> str:
    """SHA-256 over the canonical JSON (sorted keys, no whitespace) of ``record`` minus ``digest``.

    The same rule as ``datanivra_contracts.canonical.checksum`` / ``lease_evidence_digest``.
    """
    body = {k: v for k, v in record.items() if k != "digest"}
    data = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------- steps


def create_ephemeral_environment(
    api: Client, ev: Evidence, *, agent_id: str, target_ref: str, tier: str, ttl_hours: float, name: str
) -> dict[str, Any]:
    """Register an ephemeral target environment that expires after ``ttl_hours``.

    ``target_ref`` is a secret reference only the agent resolves; the pipeline never sees target
    credentials.
    """
    expires = _now() + timedelta(hours=ttl_hours)
    env = api.call(
        "POST",
        "/v1/environments",
        {
            "name": name[:120],
            "tier": tier,
            "agent_id": agent_id,
            "target_ref": target_ref,
            "ephemeral": True,
            "expires_at": expires.isoformat(),
        },
    )
    ev.step("ephemeral_environment", environment_id=env["id"], tier=tier, expires_at=expires.isoformat())
    return dict(env)


def wait_for_approval(api: Client, request_id: str, *, timeout: float) -> dict[str, Any]:
    """Poll an AWAITING_APPROVAL request until someone decides it (REV-04 ENG-020)."""
    deadline = time.monotonic() + timeout
    while True:
        request = api.call("GET", f"/v1/dataset-requests/{request_id}")
        status = request.get("status")
        if status in ("REJECTED", "CANCELLED"):
            raise PipelineError("REQUEST_REJECTED", str(status))
        if status != "AWAITING_APPROVAL":
            return dict(request)
        if time.monotonic() >= deadline:
            raise PipelineError("REQUEST_AWAITING_APPROVAL", request_id)
        time.sleep(2.0)


def request_dataset(
    api: Client,
    ev: Evidence,
    *,
    template: dict[str, Any],
    environment_id: str,
    build_id: str,
    approval_timeout: float = 1800.0,
) -> dict[str, Any]:
    """Request a dataset from ``template`` into the environment and return the created dataset.

    The idempotency key ``ci-<build_id>`` prevents duplicates when a run is retried. If the request
    needs a human approval, waits up to ``approval_timeout`` seconds for it.
    """
    body = {**template, "target_environment_id": environment_id}
    body.setdefault("justification", f"CI build {build_id}")
    request = api.call("POST", "/v1/dataset-requests", body, idempotency_key=f"ci-{build_id}")
    if request.get("status") == "AWAITING_APPROVAL":
        ev.step("dataset_request_awaiting_approval", request_id=request["id"])
        request = wait_for_approval(api, request["id"], timeout=approval_timeout)
    dataset = find_dataset(api, request["id"])
    ev.step("dataset_requested", request_id=request["id"], dataset_id=dataset["id"])
    return dataset


def find_dataset(api: Client, request_id: str, timeout: float = 60.0) -> dict[str, Any]:
    """Poll until the dataset created for ``request_id`` appears; raise DATASET_NOT_CREATED on timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for d in api.items("/v1/datasets"):
            if d.get("request_id") == request_id:
                return d
        time.sleep(1.0)
    raise PipelineError("DATASET_NOT_CREATED", request_id)


def wait_for_jobs(
    api: Client, dataset_id: str, kinds: set[str], *, timeout: float, known: set[str] | None = None
) -> list[dict[str, Any]]:
    """Wait until every job of ``kinds`` for the dataset (except ``known``) is terminal."""
    deadline = time.monotonic() + timeout
    delay = 1.0
    while True:
        jobs = [
            j
            for j in api.items(f"/v1/jobs?dataset_id={dataset_id}")
            if j["kind"] in kinds and j["id"] not in (known or set())
        ]
        if jobs and all(j["state"] in TERMINAL for j in jobs):
            return jobs
        if time.monotonic() >= deadline:
            raise PipelineError("JOB_TIMEOUT", f"{sorted(kinds)} not finished")
        time.sleep(delay)
        delay = min(delay * 1.5, 10.0)  # bounded backoff: never hammer the API, never wait forever


def verify_certified(api: Client, ev: Evidence, dataset_id: str, version: int) -> dict[str, Any]:
    """Fail unless ``version`` has a CERTIFIED report with every gate passed and a matching manifest.

    The manifest checksum must equal the one in the certification report, so the tests run against
    exactly the certified data. Returns the "pin" (dataset id, version, checksums, engine and pack
    versions, table names) used to reproduce the run later.
    """
    reports = [
        r
        for r in api.items(f"/v1/certification-reports?dataset_id={dataset_id}")
        if r["dataset_version"] == version
    ]
    if (
        not reports
        or reports[0]["status"] != "CERTIFIED"
        or not all(g["passed"] for g in reports[0]["gates"])
    ):
        raise PipelineError("NOT_CERTIFIED", f"dataset {dataset_id} v{version}")
    report = reports[0]
    manifest = api.call("GET", f"/v1/datasets/{dataset_id}/versions/{version}/manifest")
    if manifest["manifest_checksum"] != report["manifest_checksum"]:
        raise PipelineError("MANIFEST_MISMATCH", dataset_id)
    pin = {
        "dataset_id": dataset_id,
        "dataset_version": version,
        "manifest_checksum": manifest["manifest_checksum"],
        "certification_report_id": report["id"],
        "engine_version": manifest["engine_version"],
        "packs": manifest.get("packs", []),
        "tables": sorted(t["table_name"] for t in manifest["tables"]),
    }
    ev.step("certified", **{k: v for k, v in pin.items() if k != "tables"}, tables=len(pin["tables"]))
    return pin


def run_tests(ev: Evidence, command: str, pin: dict[str, Any], timeout: float) -> int:
    """Run the application's test command with the dataset pin in its environment; return its exit code.

    The API token is removed from the child environment (least privilege). A timeout returns 124, like
    the ``timeout`` utility.
    """
    env = {
        **os.environ,
        "DATANIVRA_CI_DATASET_ID": str(pin["dataset_id"]),
        "DATANIVRA_CI_DATASET_VERSION": str(pin["dataset_version"]),
        "DATANIVRA_CI_MANIFEST_CHECKSUM": str(pin["manifest_checksum"]),
    }
    env.pop("DATANIVRA_API_TOKEN", None)  # the application tests never need the API token
    started = time.monotonic()
    try:
        done = subprocess.run(shlex.split(command), env=env, timeout=timeout, check=False)  # noqa: S603
        code = done.returncode
    except subprocess.TimeoutExpired:
        code = 124
    ev.step(
        "application_tests", command=command, exit_code=code, seconds=round(time.monotonic() - started, 2)
    )
    return code


def destroy(api: Client, ev: Evidence, dataset_id: str, *, timeout: float) -> None:
    """Revoke the dataset (deprovisioning every target) and wait for the new revoke jobs to succeed.

    An ``ALREADY_REVOKED`` answer is accepted so destroy can be re-run. Raises DESTROY_INCOMPLETE unless
    every revoke job SUCCEEDED and the dataset is REVOKED.
    """
    before = {
        j["id"] for j in api.items(f"/v1/jobs?dataset_id={dataset_id}") if j["kind"] == "REVOKE_DATASET"
    }
    try:
        api.call("POST", f"/v1/datasets/{dataset_id}/revoke", {"reason_code": "CI_PIPELINE_COMPLETE"})
    except PipelineError as err:
        if err.code != "ALREADY_REVOKED":
            raise
    jobs = wait_for_jobs(api, dataset_id, {"REVOKE_DATASET"}, timeout=timeout, known=before)
    states = sorted({j["state"] for j in jobs})
    status = api.call("GET", f"/v1/datasets/{dataset_id}")["status"]
    ev.step(
        "destroyed", dataset_id=dataset_id, revoke_jobs=[j["id"] for j in jobs], states=states, status=status
    )
    if states != ["SUCCEEDED"] or status != "REVOKED":
        raise PipelineError("DESTROY_INCOMPLETE", dataset_id)


# --------------------------------------------------------------------------- commands


def cmd_run(api: Client, args: argparse.Namespace) -> int:
    """``run``: environment -> dataset request -> build -> certification check -> tests -> destroy.

    Exit 0 tests passed, 1 tests failed, 2 pipeline error. The ``finally`` block destroys the data even
    on failure unless ``--keep`` (or ``--keep-on-failure`` after failing tests) was given, and always
    writes the final evidence.
    """
    build_id = build_id_from_env()
    ev = Evidence(args.evidence, build_id)
    ev.step(
        "build_trigger",
        build_id=build_id,
        commit=os.environ.get("GITHUB_SHA"),
        ref=os.environ.get("GITHUB_REF"),
    )
    template = json.loads(Path(args.request_template).read_text("utf-8"))
    dataset_id: str | None = None
    exit_code = 2
    keep = args.keep
    try:
        env = create_ephemeral_environment(
            api,
            ev,
            agent_id=args.agent_id,
            target_ref=args.target_ref,
            tier=args.tier,
            ttl_hours=args.ttl_hours,
            name=f"ci-{build_id}",
        )
        dataset = request_dataset(
            api,
            ev,
            template=template,
            environment_id=env["id"],
            build_id=build_id,
            approval_timeout=args.timeout,
        )
        dataset_id = dataset["id"]
        jobs = wait_for_jobs(api, dataset_id, {"DATASET_BUILD"}, timeout=args.timeout)
        ev.step(
            "build_job",
            jobs=[{"id": j["id"], "state": j["state"], "error_code": j.get("error_code")} for j in jobs],
        )
        if any(j["state"] != "SUCCEEDED" for j in jobs):
            raise PipelineError("BUILD_FAILED", ",".join(str(j.get("error_code")) for j in jobs))
        pin = verify_certified(api, ev, dataset_id, 1)
        pin["environment_id"] = env["id"]
        if args.pin_out:
            Path(args.pin_out).write_text(json.dumps(pin, indent=2, sort_keys=True) + "\n", "utf-8")
            ev.step("bookmark", pin_file=str(args.pin_out), dataset_version=pin["dataset_version"])
        tests = run_tests(ev, args.test_command, pin, args.test_timeout)
        exit_code = 0 if tests == 0 else 1
        keep = keep or (exit_code != 0 and args.keep_on_failure)
    except PipelineError as err:
        ev.step("pipeline_error", code=err.code)
        exit_code = 2
    finally:
        if dataset_id is not None and not keep:
            try:
                destroy(api, ev, dataset_id, timeout=args.timeout)
            except PipelineError as err:
                ev.step("destroy_error", code=err.code)
                exit_code = 2
        elif dataset_id is not None:
            ev.step("kept", dataset_id=dataset_id, reason="--keep" if args.keep else "--keep-on-failure")
        ev.finish({0: "PASSED", 1: "TESTS_FAILED"}.get(exit_code, "PIPELINE_ERROR"), exit_code=exit_code)
    return exit_code


def cmd_provision_pin(api: Client, args: argparse.Namespace) -> int:
    """``provision-pin``: re-provision the exact certified version recorded in a pin file.

    The certification is re-verified and the manifest checksum must still match the pin, so a changed
    dataset is never silently substituted. Exit 0 provisioned, 2 error.
    """
    pin = json.loads(Path(args.pin).read_text("utf-8"))
    build_id = build_id_from_env()
    ev = Evidence(args.evidence, build_id)
    try:
        env = create_ephemeral_environment(
            api,
            ev,
            agent_id=args.agent_id,
            target_ref=args.target_ref,
            tier=args.tier,
            ttl_hours=args.ttl_hours,
            name=f"ci-repro-{build_id}",
        )
        # Re-verify: only the exact certified version recorded in the pin is provisioned.
        current = verify_certified(api, ev, pin["dataset_id"], int(pin["dataset_version"]))
        if current["manifest_checksum"] != pin["manifest_checksum"]:
            raise PipelineError("PIN_MISMATCH", pin["dataset_id"])
        before = {j["id"] for j in api.items(f"/v1/jobs?dataset_id={pin['dataset_id']}")}
        job = api.call(
            "POST",
            f"/v1/datasets/{pin['dataset_id']}/versions/{pin['dataset_version']}/provision",
            {"environment_id": env["id"]},
            idempotency_key=f"ci-pin-{build_id}",
        )
        jobs = wait_for_jobs(api, pin["dataset_id"], {job["kind"]}, timeout=args.timeout, known=before)
        ev.step(
            "provisioned_pin",
            job_id=job["id"],
            states=sorted({j["state"] for j in jobs}),
            environment_id=env["id"],
        )
        if any(j["state"] != "SUCCEEDED" for j in jobs):
            raise PipelineError("PROVISION_FAILED", pin["dataset_id"])
    except PipelineError as err:
        ev.step("pipeline_error", code=err.code)
        ev.finish("PIPELINE_ERROR", exit_code=2)
        return 2
    ev.finish("PROVISIONED", exit_code=0)
    return 0


def cmd_destroy(api: Client, args: argparse.Namespace) -> int:
    """``destroy``: revoke the dataset named in a pin file; exit 0 destroyed, 2 error."""
    pin = json.loads(Path(args.pin).read_text("utf-8"))
    ev = Evidence(args.evidence, build_id_from_env())
    try:
        destroy(api, ev, pin["dataset_id"], timeout=args.timeout)
    except PipelineError as err:
        ev.step("pipeline_error", code=err.code)
        ev.finish("PIPELINE_ERROR", exit_code=2)
        return 2
    ev.finish("DESTROYED", exit_code=0)
    return 0


# --------------------------------------------------------------------------- lease mode


def _lease_fields(lease: dict[str, Any]) -> dict[str, Any]:
    """The metadata of a lease that goes into the step log (ids, states, reason codes, times)."""
    keys = ("state", "state_reason_code", "environment_id", "expires_at", "ready_at", "cleanup_confirmed_at")
    return {"lease_id": lease["id"], **{k: lease.get(k) for k in keys}}


def request_lease(api: Client, ev: Evidence, args: argparse.Namespace, build_id: str) -> dict[str, Any]:
    """``POST /v1/environment-leases`` with the CI reference and a deterministic idempotency key."""
    body: dict[str, Any] = {"dataset_id": args.dataset_id, "ttl_seconds": int(args.ttl_minutes * 60)}
    if args.dataset_version is not None:
        body["dataset_version"] = args.dataset_version
    if args.environment_id:
        body["environment_id"] = args.environment_id
    else:
        if not (args.agent_id and args.target_ref):
            raise PipelineError("LEASE_TARGET_MISSING", "give --environment-id or --agent-id + --target-ref")
        body["target"] = {
            "agent_id": args.agent_id,
            "target_ref": args.target_ref,
            "tier": args.tier,
            "provider_kind": args.provider_kind,
            "name": f"lease-{build_id}"[:120],
        }
    if args.purpose_ref:
        body["purpose_ref"] = args.purpose_ref
    ci = ci_context_from_env()
    if ci is not None:
        body["ci_ref"] = ci.ci_ref()
        request = json.dumps({k: v for k, v in body.items() if k != "ci_ref"}, sort_keys=True)
        key = ci.idempotency_key("createEnvironmentLease", hashlib.sha256(request.encode()).hexdigest())
    else:
        key = "lease-" + re.sub(r"[^A-Za-z0-9._:-]", "-", build_id)[:90]
    lease = api.call("POST", "/v1/environment-leases", body, idempotency_key=key)
    ev.step("lease_requested", ci_ref=body.get("ci_ref"), dataset_id=args.dataset_id, **_lease_fields(lease))
    return dict(lease)


def wait_for_lease(api: Client, ev: Evidence, lease: dict[str, Any], *, timeout: float) -> dict[str, Any]:
    """Poll until READY; an ended lease is ``LEASE_ENDED``, the timeout ``LEASE_TIMEOUT``."""
    deadline = time.monotonic() + timeout
    delay = 1.0
    while lease["state"] in LEASE_WAITING:
        if time.monotonic() >= deadline:
            raise PipelineError("LEASE_TIMEOUT", str(lease["id"]))
        time.sleep(delay)
        delay = min(delay * 1.5, 10.0)
        lease = api.call("GET", f"/v1/environment-leases/{lease['id']}")
    ev.step("lease_ready" if lease["state"] == "READY" else "lease_not_ready", **_lease_fields(lease))
    if lease["state"] != "READY":
        raise PipelineError("LEASE_ENDED", f"{lease['state']}:{lease.get('state_reason_code')}")
    return dict(lease)


def run_lease_tests(ev: Evidence, command: str, lease: dict[str, Any], timeout: float) -> int:
    """Run the test command with the lease ids in its environment (never the API token)."""
    env = {
        **os.environ,
        "DATANIVRA_CI_LEASE_ID": str(lease["id"]),
        "DATANIVRA_CI_DATASET_ID": str(lease["dataset_id"]),
        "DATANIVRA_CI_DATASET_VERSION": str(lease["dataset_version"]),
        "DATANIVRA_CI_ENVIRONMENT_ID": str(lease["environment_id"]),
    }
    env.pop("DATANIVRA_API_TOKEN", None)
    started = time.monotonic()
    try:
        code = subprocess.run(shlex.split(command), env=env, timeout=timeout, check=False).returncode  # noqa: S603
    except subprocess.TimeoutExpired:
        code = 124
    ev.step(
        "application_tests", command=command, exit_code=code, seconds=round(time.monotonic() - started, 2)
    )
    return code


def release_lease(api: Client, ev: Evidence, lease_id: str, *, reason: str, timeout: float) -> dict[str, Any]:
    """Release (idempotent) and wait until the agent confirmed the teardown."""
    lease = api.call("POST", f"/v1/environment-leases/{lease_id}/release", {"reason_code": reason})
    deadline = time.monotonic() + timeout
    delay = 1.0
    while lease["state"] not in LEASE_ENDED or not lease.get("cleanup_confirmed_at"):
        if time.monotonic() >= deadline:
            ev.step("lease_release_pending", **_lease_fields(lease))
            raise PipelineError("LEASE_TEARDOWN_UNCONFIRMED", lease_id)
        time.sleep(delay)
        delay = min(delay * 1.5, 10.0)
        lease = api.call("GET", f"/v1/environment-leases/{lease_id}")
    ev.step("lease_released", reason_code=reason, **_lease_fields(lease))
    return dict(lease)


def lease_evidence(api: Client, ev: Evidence, lease_id: str, out: Path | None) -> dict[str, Any]:
    """Download the value-free lease evidence and verify its digest (``LEASE_EVIDENCE_DIGEST_MISMATCH``)."""
    record = api.call("GET", f"/v1/environment-leases/{lease_id}/evidence")
    if canonical_digest(record) != record.get("digest"):
        ev.step("lease_evidence", lease_id=lease_id, digest_verified=False)
        raise PipelineError("LEASE_EVIDENCE_DIGEST_MISMATCH", lease_id)
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", "utf-8")
    ev.step(
        "lease_evidence",
        lease_id=lease_id,
        state=record["state"],
        digest=record["digest"],
        digest_verified=True,
        certificate_id=record["certificate"]["certificate_id"],
        events=[e["state"] for e in record["events"]],
        receipts=[{"purpose": r["purpose"], "state": r["state"]} for r in record["receipts"]],
    )
    return dict(record)


def cmd_lease(api: Client, args: argparse.Namespace) -> int:
    """``lease``: request -> wait READY -> test -> release -> evidence. Exit 0 / 1 tests / 2 error.

    The release runs in ``finally`` (unless ``--keep-on-failure`` after failing tests), so a test
    failure or a pipeline error never leaves the environment behind; the lease TTL is the
    backstop if the runner itself dies.
    """
    build_id = build_id_from_env()
    ev = Evidence(args.evidence, build_id)
    ci = ci_context_from_env()
    ev.step("build_trigger", build_id=build_id, ci_ref=ci.ci_ref() if ci else None)
    lease_id: str | None = None
    exit_code = 2
    keep = False
    try:
        lease = request_lease(api, ev, args, build_id)
        lease_id = str(lease["id"])
        lease = wait_for_lease(api, ev, lease, timeout=args.timeout)
        tests = run_lease_tests(ev, args.test_command, lease, args.test_timeout)
        exit_code = 0 if tests == 0 else 1
        keep = exit_code == 1 and args.keep_on_failure
    except PipelineError as err:
        ev.step("pipeline_error", code=err.code)
        exit_code = 2
    finally:
        if lease_id is not None and keep:
            ev.step("kept", lease_id=lease_id, reason="--keep-on-failure (lapses at its TTL)")
        elif lease_id is not None:
            try:
                release_lease(api, ev, lease_id, reason=args.reason_code, timeout=args.timeout)
                lease_evidence(api, ev, lease_id, args.lease_evidence_out)
            except PipelineError as err:
                ev.step("release_error", code=err.code)
                exit_code = 2
        ev.finish(
            {0: "PASSED", 1: "TESTS_FAILED"}.get(exit_code, "PIPELINE_ERROR"),
            exit_code=exit_code,
            lease_id=lease_id,
        )
    return exit_code


def cmd_lease_cleanup(api: Client, args: argparse.Namespace) -> int:
    """``lease-cleanup``: release every live lease of one pull request (``pull_request: closed``).

    Matches provider + repository (case-insensitive) + PR number of each live lease's ``ci_ref``;
    ``--this-run`` also requires the current CI run id, so the ``if: always()`` backstop step of
    one run never touches another run's lease. Idempotent. Exit 0 done (also when nothing was
    live), 2 error.
    """
    ev = Evidence(args.evidence, build_id_from_env())
    ci = ci_context_from_env()
    provider = args.ci_provider or (ci.provider if ci else None)
    repository = args.repository or (ci.repository if ci else None)
    pr = args.pr if args.pr is not None else (ci.pr_number if ci else None)
    run_id = ci.run_id if ci else None
    try:
        if not provider or not repository or pr is None or not _REPOSITORY.match(repository):
            raise PipelineError(
                "CI_CONTEXT_MISSING", "give --repository and --pr (or run inside the PR's CI job)"
            )
        if args.this_run and run_id is None:
            raise PipelineError("CI_CONTEXT_MISSING", "--this-run needs the CI run id from the environment")
        released: list[str] = []
        for state in sorted(LEASE_LIVE):
            for lease in api.items(f"/v1/environment-leases?state={state}"):
                ref = lease.get("ci_ref") or {}
                if (
                    ref.get("provider") == provider
                    and str(ref.get("repository", "")).lower() == repository.lower()
                    and ref.get("pr_number") == pr
                    and (not args.this_run or ref.get("run_id") == run_id)
                ):
                    api.call(
                        "POST",
                        f"/v1/environment-leases/{lease['id']}/release",
                        {"reason_code": args.reason_code},
                    )
                    released.append(str(lease["id"]))
        ev.step(
            "lease_cleanup",
            provider=provider,
            repository=repository,
            pr_number=pr,
            run_id=run_id if args.this_run else None,
            released=released,
        )
    except PipelineError as err:
        ev.step("pipeline_error", code=err.code)
        ev.finish("PIPELINE_ERROR", exit_code=2)
        return 2
    ev.finish("CLEANED_UP", exit_code=0)
    return 0


def parser() -> argparse.ArgumentParser:
    """Build the CLI parser with the ``run``, ``provision-pin`` and ``destroy`` sub-commands."""
    p = argparse.ArgumentParser(prog="datanivra_ci.py", description=__doc__.split("\n", 1)[0])
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp: argparse.ArgumentParser, *, target: bool) -> None:
        """Add the options shared by sub-commands; ``target`` adds the target-environment options."""
        sp.add_argument("--evidence", type=Path, default=None, help="write the JSON evidence record here")
        sp.add_argument("--timeout", type=float, default=1800.0, help="seconds to wait for each job group")
        if target:
            sp.add_argument("--agent-id", required=True, help="agent that provisions the ephemeral target")
            sp.add_argument("--target-ref", required=True, help="secret reference the agent resolves")
            sp.add_argument("--tier", default="DEV", choices=["DEV", "QA", "SIT", "UAT", "PERF"])
            sp.add_argument("--ttl-hours", type=float, default=4.0, help="ephemeral environment lifetime")

    run = sub.add_parser("run", help="full pipeline: request, wait, test, destroy")
    common(run, target=True)
    run.add_argument("--request-template", required=True, help="JSON dataset request (without target)")
    run.add_argument("--test-command", required=True, help="application test command")
    run.add_argument("--test-timeout", type=float, default=3600.0)
    run.add_argument("--pin-out", type=Path, default=None, help="write the dataset version pin here")
    run.add_argument("--keep", action="store_true", help="never destroy (debugging)")
    run.add_argument("--keep-on-failure", action="store_true", help="keep the data when tests fail")
    prov = sub.add_parser("provision-pin", help="provision a pinned certified version (reproduce)")
    prov.add_argument("pin", type=Path)
    common(prov, target=True)
    dest = sub.add_parser(
        "destroy", help="revoke a pinned dataset and deprovision every target (lease release preferred)"
    )
    dest.add_argument("pin", type=Path)
    common(dest, target=False)

    lease = sub.add_parser("lease", help="lease a certified version: request, wait, test, release")
    common(lease, target=False)
    lease.add_argument("--dataset-id", required=True, help="dataset whose certified version is leased")
    lease.add_argument("--dataset-version", type=int, default=None, help="default: the current version")
    lease.add_argument("--environment-id", default=None, help="attach an existing ephemeral environment")
    lease.add_argument("--agent-id", default=None, help="agent serving a new target (with --target-ref)")
    lease.add_argument("--target-ref", default=None, help="secret reference the agent resolves")
    lease.add_argument("--tier", default="QA", choices=["DEV", "QA", "SIT", "UAT", "PERF"])
    lease.add_argument("--provider-kind", default="CUSTOMER_MANAGED", help="e.g. POSTGRESQL_CONTAINER")
    lease.add_argument("--ttl-minutes", type=float, default=60.0, help="lease lifetime unless renewed")
    lease.add_argument("--purpose-ref", default=None, help="ticket, e.g. QA-1234")
    lease.add_argument("--test-command", required=True, help="application test command")
    lease.add_argument("--test-timeout", type=float, default=3600.0)
    lease.add_argument("--reason-code", default="TEST_RUN_FINISHED", help="release reason code")
    lease.add_argument("--keep-on-failure", action="store_true", help="keep the lease when tests fail")
    lease.add_argument("--lease-evidence-out", type=Path, default=None, help="write the lease evidence here")

    cleanup = sub.add_parser("lease-cleanup", help="release every live lease of a pull request")
    common(cleanup, target=False)
    cleanup.add_argument("--ci-provider", default=None, help="default: from the CI environment")
    cleanup.add_argument("--repository", default=None, help="default: from the CI environment")
    cleanup.add_argument("--pr", type=int, default=None, help="default: from the CI environment")
    cleanup.add_argument("--reason-code", default="PR_CLOSED", help="release reason code")
    cleanup.add_argument(
        "--this-run", action="store_true", help="only leases of the current CI run (always() backstop)"
    )
    return p


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: read the API URL and token from the environment and dispatch the sub-command."""
    args = parser().parse_args(argv)
    url, token = os.environ.get("DATANIVRA_API_URL"), os.environ.get("DATANIVRA_API_TOKEN")
    if not url or not token:
        print("DATANIVRA_API_URL and DATANIVRA_API_TOKEN must be set", file=sys.stderr)  # noqa: T201
        return 2
    try:
        api = Client(url, token)
    except PipelineError as err:
        print(err.code, file=sys.stderr)  # noqa: T201
        return 2
    handlers = {
        "run": cmd_run,
        "provision-pin": cmd_provision_pin,
        "destroy": cmd_destroy,
        "lease": cmd_lease,
        "lease-cleanup": cmd_lease_cleanup,
    }
    return handlers[args.command](api, args)


if __name__ == "__main__":
    sys.exit(main())
