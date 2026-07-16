"""Exercise the production API, Postgres, Redis worker and shared artifact store.

Run after ``docker compose up --detach``. The script uses only the Python standard
library so the same contract can run from a developer machine or GitHub Actions.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_URL = os.environ.get("ATLAS_E2E_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
COMPOSE_PROJECT_NAME = os.environ.get("COMPOSE_PROJECT_NAME", "").strip()
STARTUP_TIMEOUT_SECONDS = 120
ANALYSIS_TIMEOUT_SECONDS = 180


class SmokeTestError(RuntimeError):
    """Raised when the deployed stack violates an expected contract."""


def _request(
    method: str,
    path: str,
    *,
    token: str | None = None,
    payload: dict[str, Any] | None = None,
    expected_status: int = 200,
) -> tuple[bytes, dict[str, str]]:
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["X-API-Key"] = token

    request = Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=15) as response:
            body = response.read()
            status = response.status
            response_headers = {key.lower(): value for key, value in response.headers.items()}
    except HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise SmokeTestError(f"{method} {path} returned {exc.code}: {detail}") from exc
    except (URLError, OSError) as exc:
        reason = getattr(exc, "reason", str(exc))
        raise SmokeTestError(f"{method} {path} failed: {reason}") from exc

    if status != expected_status:
        raise SmokeTestError(f"{method} {path} returned {status}, expected {expected_status}")
    return body, response_headers


def _json_request(
    method: str,
    path: str,
    *,
    token: str | None = None,
    payload: dict[str, Any] | None = None,
    expected_status: int = 200,
) -> dict[str, Any]:
    body, _ = _request(
        method,
        path,
        token=token,
        payload=payload,
        expected_status=expected_status,
    )
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise SmokeTestError(f"{method} {path} did not return JSON") from exc
    if not isinstance(parsed, dict):
        raise SmokeTestError(f"{method} {path} returned an unexpected JSON value")
    return parsed


def _wait_for_stack() -> None:
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    last_error = "API did not answer"
    while time.monotonic() < deadline:
        try:
            health = _json_request("GET", "/health")
            if health.get("status") == "ok":
                checks = health.get("checks", {})
                if checks.get("database") == "ok" and checks.get("queue") == "ok":
                    return
            last_error = f"health payload: {health}"
        except SmokeTestError as exc:
            last_error = str(exc)
        time.sleep(2)
    raise SmokeTestError(f"stack was not ready after {STARTUP_TIMEOUT_SECONDS}s: {last_error}")


def _seed() -> tuple[str, str]:
    completed = subprocess.run(
        ["docker", "compose", "exec", "-T", "api", "python", "-m", "atlas.interfaces.cli", "seed"],
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    if completed.returncode != 0:
        raise SmokeTestError(f"seed command failed: {completed.stderr.strip()}")

    token_match = re.search(r"^api_key\s*:\s*(atlas_\S+)", completed.stdout, re.MULTILINE)
    snapshot_match = re.search(r"^snapshot_id\s*:\s*(\S+)", completed.stdout, re.MULTILINE)
    if not token_match or not snapshot_match:
        raise SmokeTestError("seed command did not return an API key and snapshot id")
    return token_match.group(1), snapshot_match.group(1)


def _wait_for_analysis(job_id: str, token: str) -> dict[str, Any]:
    deadline = time.monotonic() + ANALYSIS_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        analysis = _json_request("GET", f"/analyses/{job_id}", token=token)
        status = analysis.get("status")
        if status == "succeeded":
            return analysis
        if status == "failed":
            raise SmokeTestError(f"worker failed analysis {job_id}: {analysis.get('error')}")
        time.sleep(1)
    raise SmokeTestError(f"analysis {job_id} did not finish after {ANALYSIS_TIMEOUT_SECONDS}s")


def run() -> None:
    if not COMPOSE_PROJECT_NAME:
        raise SmokeTestError(
            "set COMPOSE_PROJECT_NAME to an isolated test project before running the E2E"
        )
    _wait_for_stack()
    _, root_headers = _request("GET", "/")
    if root_headers.get("x-atlas-frontend") != "react":
        raise SmokeTestError("production root did not serve the packaged React interface")
    token, snapshot_id = _seed()

    portfolio = _json_request(
        "POST",
        "/portfolios",
        token=token,
        expected_status=201,
        payload={
            "name": "Compose E2E Portfolio",
            "companies": [
                {
                    "name": "E2E Industrials",
                    "sector": "industrials",
                    "geography": "US",
                    "ebitda": 100.0,
                    "multiple": 8.0,
                    "carrying_value": 760.0,
                    "debt": 300.0,
                    "cash": 50.0,
                    "debt_due_1y": 60.0,
                }
            ],
        },
    )
    job = _json_request(
        "POST",
        "/analyses",
        token=token,
        expected_status=202,
        payload={"engine": "impairment", "portfolio_id": portfolio["portfolio_id"]},
    )
    analysis = _wait_for_analysis(job["job_id"], token)

    if analysis.get("snapshot_id") != snapshot_id:
        raise SmokeTestError("worker used a different snapshot from the seeded snapshot")
    if analysis.get("attempts", 0) < 1:
        raise SmokeTestError("analysis did not record a worker execution attempt")

    result = analysis.get("result") or {}
    probability = (result.get("metrics") or {}).get("portfolio_mean_p_impairment")
    if not isinstance(probability, int | float) or not 0 <= probability <= 1:
        raise SmokeTestError("analysis result is missing a valid impairment probability")

    artifacts = result.get("artifacts") or []
    if not artifacts:
        raise SmokeTestError("worker did not publish artifacts")
    for artifact in artifacts:
        body, _ = _request(
            "GET",
            f"/artifacts/{job['job_id']}/{artifact['name']}",
            token=token,
        )
        if len(body) != artifact["size_bytes"]:
            raise SmokeTestError(f"artifact {artifact['name']} size does not match its manifest")

    report = _json_request(
        "POST",
        f"/analyses/{job['job_id']}/report",
        token=token,
        expected_status=201,
    )
    persisted = _json_request("GET", f"/analyses/{job['job_id']}/report", token=token)
    if report.get("report_id") != persisted.get("report_id"):
        raise SmokeTestError("persisted report does not match the created report")
    if persisted.get("run_id") != job["job_id"]:
        raise SmokeTestError("report does not reference the completed analysis")

    print("compose e2e: API, Postgres, Redis worker, artifacts and report OK")


if __name__ == "__main__":
    run()
