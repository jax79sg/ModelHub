"""A PostgreSQL fixture for tests (BQ2).

``fresh_database`` gives each test its own empty database. The server comes from, in order:
the ``MODELHUB_TEST_POSTGRES_URL`` variable (CI service container), or a throwaway PostgreSQL 16
container started through the Docker command line. When neither is available the tests skip
with a clear message.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
import uuid

import pytest

IMAGE = os.environ.get("MODELHUB_TEST_POSTGRES_IMAGE", "postgres:16")
ADMIN_ENV = "MODELHUB_TEST_POSTGRES_URL"


def _docker_ready() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        result = subprocess.run(["docker", "info"], capture_output=True, timeout=20, check=False)
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _wait_ready(url: str, seconds: float = 60) -> None:
    import psycopg

    deadline = time.monotonic() + seconds
    last = None
    while time.monotonic() < deadline:
        try:
            with psycopg.connect(url, connect_timeout=2):
                return
        except psycopg.OperationalError as exc:
            last = exc
            time.sleep(0.5)
    raise RuntimeError(f"PostgreSQL did not become ready: {last}")


@pytest.fixture(scope="session")
def postgres_admin_url():
    url = os.environ.get(ADMIN_ENV)
    if url:
        _wait_ready(url)
        yield url
        return
    if not _docker_ready():
        pytest.skip(f"needs PostgreSQL: set {ADMIN_ENV} or start Docker")
    name = "modelhub-test-pg-" + uuid.uuid4().hex[:8]
    started = _docker(
        [
            "run",
            "-d",
            "--rm",
            "--name",
            name,
            "-e",
            "POSTGRES_PASSWORD=test",
            "-p",
            "127.0.0.1::5432",
            IMAGE,
        ],
        timeout=120,
    )
    if started is None or started.returncode != 0:
        pytest.skip("Docker did not start the PostgreSQL container")
    try:
        out = _docker(["port", name, "5432/tcp"], timeout=20)
        if out is None or out.returncode != 0:
            pytest.skip("Docker did not answer for the PostgreSQL container")
        port = out.stdout.splitlines()[0].rsplit(":", 1)[1]
        url = f"postgresql://postgres:test@127.0.0.1:{port}/postgres"
        _wait_ready(url)
        yield url
    finally:
        _stop_postgres(name)


def _docker(args: list[str], timeout: float):
    """Run a docker command that cannot hang the tests; None when it times out."""
    try:
        return subprocess.run(
            ["docker", *args], capture_output=True, text=True, timeout=timeout, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def _stop_postgres(name: str) -> None:
    """Kill PostgreSQL inside the container first, then stop the container.

    PostgreSQL can hold on while Docker tears its container down (seen to leave OrbStack stuck).
    SIGQUIT to the server process (PID 1 in this image) is an immediate shutdown that does not wait
    for clients. The container was started with --rm, so Docker removes it once it has stopped; we
    never ask for a second removal.
    """
    _docker(["exec", name, "sh", "-c", "kill -s QUIT 1"], timeout=20)
    _docker(["stop", "-t", "2", name], timeout=30)


@pytest.fixture
def fresh_database(postgres_admin_url):
    """The URL of a new, empty database that exists only for this test."""
    import psycopg

    name = "t_" + uuid.uuid4().hex[:12]
    with psycopg.connect(postgres_admin_url, autocommit=True) as admin:
        admin.execute(f'create database "{name}"')
    base, _, _ = postgres_admin_url.rpartition("/")
    yield f"{base}/{name}"
    with psycopg.connect(postgres_admin_url, autocommit=True) as admin:
        admin.execute(f'drop database if exists "{name}" with (force)')
