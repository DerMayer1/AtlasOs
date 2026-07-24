"""Render web-service entrypoint: migrate, then run the worker and API together.

Render persistent disks attach to exactly one service, but both the API (reads
artifacts for downloads, reports and citation validation) and the Arq worker
(writes snapshots and artifacts) need the same ``/data`` volume. So they run as
two processes in this one service, sharing the disk. Jobs still flow through
Redis and execute in the worker process — not the API event loop — so a heavy
analysis never blocks request handling.

If either child exits, this supervisor tears the other down and exits non-zero
so Render restarts the whole service. Independent worker scaling would require
moving artifacts to object storage (see docs/DEPLOY.md); that is the S3 path.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time

PORT = os.environ.get("PORT", "8000")

MIGRATE = [sys.executable, "-m", "atlas.interfaces.cli", "init-db"]
WORKER = ["arq", "atlas.interfaces.worker.WorkerSettings"]
API = [
    "uvicorn",
    "atlas.interfaces.api.app:create_app",
    "--factory",
    "--host",
    "0.0.0.0",
    "--port",
    PORT,
]


def _run_migrations() -> None:
    print("[render_start] applying migrations (alembic upgrade head)", flush=True)
    subprocess.run(MIGRATE, check=True)


def main() -> int:
    _run_migrations()

    print("[render_start] starting worker and API", flush=True)
    children: dict[str, subprocess.Popen] = {
        "worker": subprocess.Popen(WORKER),
        "api": subprocess.Popen(API),
    }

    stopping = False

    def _terminate(*_args: object) -> None:
        nonlocal stopping
        stopping = True
        for name, proc in children.items():
            if proc.poll() is None:
                print(f"[render_start] terminating {name}", flush=True)
                proc.terminate()

    signal.signal(signal.SIGTERM, _terminate)
    signal.signal(signal.SIGINT, _terminate)

    # Supervise: if either process exits, bring the whole service down so the
    # platform restarts it, rather than limp along with half the stack missing.
    exit_code = 0
    while not stopping:
        for name, proc in children.items():
            code = proc.poll()
            if code is not None:
                print(f"[render_start] {name} exited with {code}; shutting down", flush=True)
                exit_code = code or 1
                _terminate()
                break
        time.sleep(1.0)

    deadline = time.monotonic() + 10.0
    for proc in children.values():
        remaining = max(0.0, deadline - time.monotonic())
        try:
            proc.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            proc.kill()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
