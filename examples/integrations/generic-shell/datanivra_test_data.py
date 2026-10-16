#!/usr/bin/env python3
"""Generic CI recipe (ADR-0018) — Python standard library only, REST only, no SDK.

    DATANIVRA_BASE_URL=https://api.example.test DATANIVRA_TOKEN=... \
      python3 datanivra_test_data.py ../request.json -- ./scripts/run-integration-tests.sh

(sign in) -> request -> wait READY -> run the test command -> release in ``finally``.
Exit codes: the test command's status; 24 denied by the profile; 25 still pending a human approval;
26 ended without READY; 27 timed out; 143 cancelled by SIGTERM (after releasing and stopping the
test command); 1 other API errors.

Credentials: ``DATANIVRA_TOKEN`` (a session), or a workload identity exchange with
``DATANIVRA_ID_TOKEN`` (your CI's OIDC token) + ``DATANIVRA_TENANT`` +
``DATANIVRA_WORKLOAD_IDENTITY_ID``. Only ids, states and reason codes are printed (stderr); the token
is never printed, logged or placed on a command line. DataNivra never returns rows or credentials.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from typing import Any

TERMINAL = {"RELEASED", "REJECTED", "CANCELLED", "FAILED"}
EXIT_DENIED, EXIT_PENDING, EXIT_ENDED, EXIT_TIMEOUT = 24, 25, 26, 27
EXIT_CANCELLED = 143  # 128 + SIGTERM, as a shell reports a job ended by SIGTERM

# (method, url, headers, body) -> (status, parsed JSON body). Injectable for tests.
Send = Callable[[str, str, Mapping[str, str], bytes | None], tuple[int, Any]]


LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


def check_base_url(url: str) -> str:
    """https, or http only to a loopback host; no userinfo, query or fragment (fail closed)."""
    parts = urllib.parse.urlsplit(url)
    host = (parts.hostname or "").lower()
    loopback_http = parts.scheme == "http" and host in LOOPBACK_HOSTS
    if (parts.scheme != "https" and not loopback_http) or not host:
        raise SystemExit("DATANIVRA_BASE_URL must be https:// (the token must not travel unencrypted)")
    if parts.username or parts.password or parts.query or parts.fragment:
        raise SystemExit("DATANIVRA_BASE_URL must not contain credentials, a query or a fragment")
    return url.rstrip("/")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Never follow redirects: a 3xx would forward the bearer token to another origin."""

    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def urllib_send(method: str, url: str, headers: Mapping[str, str], body: bytes | None) -> tuple[int, Any]:
    """One HTTPS request with the standard library; redirects are refused, never followed."""
    check_base_url(url.split("/v1/", 1)[0])
    request = urllib.request.Request(url, data=body, method=method, headers=dict(headers))  # noqa: S310
    try:
        with _OPENER.open(request, timeout=30) as response:
            return response.status, json.loads(response.read() or b"null")
    except urllib.error.HTTPError as error:
        if 300 <= error.code < 400:
            return error.code, {"code": "REDIRECT_REFUSED"}
        return error.code, json.loads(error.read() or b"null")


class ApiError(Exception):
    """A non-2xx answer: HTTP status and the API error code (never a submitted value)."""

    def __init__(self, status: int, payload: Any) -> None:
        self.status = status
        self.code = payload.get("code", "ERROR") if isinstance(payload, dict) else "ERROR"
        self.reasons = (
            [d.get("code") for d in payload.get("details", [])] if isinstance(payload, dict) else []
        )
        super().__init__(f"HTTP {status} {self.code}")


class Api:
    """Minimal client for the five Test Data API calls this recipe needs."""

    def __init__(self, base_url: str, token: str, send: Send = urllib_send) -> None:
        self.base, self._token, self._send = check_base_url(base_url), token, send

    def call(self, method: str, path: str, body: Any = None, key: str | None = None) -> Any:
        headers = {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"}
        if key:
            headers["Idempotency-Key"] = key
        data = json.dumps(body).encode() if body is not None else None
        status, payload = self._send(method, self.base + path, headers, data)
        if status >= 400:
            raise ApiError(status, payload)
        return payload


def exchange_workload_token(base_url: str, env: Mapping[str, str], send: Send = urllib_send) -> str:
    """CI OIDC token -> short workload session token (``POST /v1/auth/workload/token``)."""
    body = {
        "id_token": env["DATANIVRA_ID_TOKEN"],
        "tenant_slug": env["DATANIVRA_TENANT"],
        "workload_identity_id": env["DATANIVRA_WORKLOAD_IDENTITY_ID"],
    }
    status, payload = send(
        "POST",
        check_base_url(base_url) + "/v1/auth/workload/token",
        {"Content-Type": "application/json"},
        json.dumps(body).encode(),
    )
    if status != 200:
        raise ApiError(status, payload)
    return str(payload["access_token"])


def run(
    manifest: Mapping[str, Any],
    test_command: Sequence[str],
    *,
    api: Api,
    idempotency_key: str,
    timeout_seconds: float = 1200,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
    runner: Callable[[Sequence[str]], int] = lambda cmd: subprocess.call(list(cmd)),  # noqa: S603
    log: Callable[[str], None] = lambda line: sys.stderr.write(line + "\n") and None,
) -> int:
    """The whole recipe; returns the process exit code. Always releases what it requested."""
    if manifest.get("kind") != "TestDataRequest":
        raise SystemExit("expected a TestDataRequest manifest")
    try:
        created = api.call("POST", "/v1/test-data/requests", manifest["spec"], key=idempotency_key)
    except ApiError as error:
        if error.code == "TEST_DATA_REQUEST_DENIED":
            log(f"datanivra: denied: {', '.join(r for r in error.reasons if r)}")
            return EXIT_DENIED
        log(f"datanivra: request failed: {error}")
        return 1
    request_id = created["id"]
    log(f"datanivra: request {request_id} decision {created['decision']}")
    try:
        deadline, delay = clock() + timeout_seconds, 2.0
        while True:
            current = api.call("GET", f"/v1/test-data/requests/{request_id}")
            state = current["state"]
            if state == "READY":
                break
            if state in TERMINAL:
                log(
                    f"datanivra: request ended as {state} ({current.get('state_reason_code') or 'no reason'})"
                )
                return EXIT_ENDED
            if clock() >= deadline:
                log(f"datanivra: still {state} after {timeout_seconds:.0f}s")
                return EXIT_PENDING if state == "PENDING_APPROVAL" else EXIT_TIMEOUT
            sleep(delay)
            delay = min(delay * 2, 30.0)
        log(f"datanivra: READY environment {current.get('environment_id')}")
        return runner(test_command)
    finally:
        try:
            api.call(
                "POST", f"/v1/test-data/requests/{request_id}/release", {"reason_code": "TEST_RUN_FINISHED"}
            )
            log(f"datanivra: released {request_id}")
        except ApiError as error:  # never mask the test result; the lease TTL still tears down
            log(f"datanivra: release failed ({error}); the lease ends at its TTL")


class Cancelled(Exception):
    """The CI system cancelled the job (SIGTERM)."""


def _on_sigterm(_signum: int, _frame: object) -> None:
    """Unwind through ``run``'s ``finally`` (release) instead of dying on the spot.

    Python's default SIGTERM action exits without running ``finally`` blocks. Further SIGTERMs are
    ignored so the release call itself is not interrupted. ``subprocess.call`` kills the running
    test command when the exception passes through it.
    """
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    raise Cancelled


def main(argv: Sequence[str], env: Mapping[str, str] = os.environ) -> int:
    """Command-line entry point (see the module docstring)."""
    if len(argv) < 3 or argv[1] != "--":
        raise SystemExit("usage: datanivra_test_data.py REQUEST.json -- TEST COMMAND...")
    base_url = env.get("DATANIVRA_BASE_URL") or ""
    token = env.get("DATANIVRA_TOKEN") or exchange_workload_token(base_url, env)
    with open(argv[0], encoding="utf-8") as handle:
        manifest = json.load(handle)
    key = env.get("DATANIVRA_IDEMPOTENCY_KEY") or f"py-{int(time.time())}-{os.getpid()}"
    signal.signal(signal.SIGTERM, _on_sigterm)
    try:
        return run(manifest, list(argv[2:]), api=Api(base_url, token), idempotency_key=key)
    except Cancelled:
        sys.stderr.write("datanivra: cancelled (SIGTERM); released what was requested\n")
        return EXIT_CANCELLED


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
