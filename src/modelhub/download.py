"""Downloading many files: at the same time, with retries, checked against the Hub's checksums."""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from modelhub import fsutil
from modelhub.hubclient import HubClient, HubError, RateLimited, TransientHubError
from modelhub.progress import NullReporter

logger = logging.getLogger("modelhub.download")

DEFAULT_WORKERS = 8  # the same default as Hugging Face's own tool (NFR1.2)


class ChecksumMismatch(Exception):
    """A downloaded file does not match the checksum Hugging Face reports for it."""


def hub_checksum_ok(path: Path, hub_entry: dict) -> bool:
    """Compare a file with the checksum Hugging Face reported (FR5.4)."""
    lfs = hub_entry.get("lfs") or {}
    if lfs.get("oid"):
        return fsutil.sha256_file(path) == lfs["oid"]
    if hub_entry.get("oid"):
        return fsutil.git_blob_sha1(path) == hub_entry["oid"]
    return True


@dataclass
class RetryPolicy:
    """Up to five retries, waiting 1, 2, 4, 8 and 16 seconds plus a small random extra (NFR3.5)."""

    retries: int = 5
    waits: tuple[float, ...] = (1, 2, 4, 8, 16)
    jitter: float = 0.25
    rng: random.Random = field(default_factory=random.Random)

    def wait_for(self, attempt: int) -> float:
        base = self.waits[min(attempt, len(self.waits) - 1)]
        return base + base * self.jitter * self.rng.random()


@dataclass
class FetchOutcome:
    fetched: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: list[dict] = field(default_factory=list)
    items: list[dict] = field(default_factory=list)  # every file, for the run record


def _fetch_one(
    client: HubClient,
    repo: str,
    commit: str,
    entry: dict,
    dest: Path,
    policy: RetryPolicy,
    sleep: Callable[[float], None],
    on_wait: Callable[[str], None] | None,
    progress,
    stats: dict,
) -> str:
    path = entry["path"]
    if dest.is_file() and hub_checksum_ok(dest, entry):
        progress.advance(entry.get("size", 0), item=path, item_done=True)
        return "skipped"  # fetched and checked on an earlier run: not fetched again (FR5.3)
    progress.advance(0, item=path)
    attempt = 0
    while True:
        reported = {"bytes": 0}

        def count(n: int, reported=reported) -> None:
            reported["bytes"] += n
            progress.advance(n)

        try:
            client.download_file(repo, commit, path, dest, progress_cb=count)
            break
        except RateLimited as error:
            progress.advance(-reported["bytes"])
            if attempt >= policy.retries:
                raise
            wait = error.retry_after if error.retry_after is not None else policy.wait_for(attempt)
            _tell(on_wait, f"Hugging Face asked us to slow down; waiting {wait:g} s ({path})")
            logger.info("%s: rate limited; trying again in %g s", path, wait)
            sleep(wait)
            attempt += 1
            stats["retries"] = attempt
        except TransientHubError as error:
            progress.advance(-reported["bytes"])
            if attempt >= policy.retries:
                raise
            wait = policy.wait_for(attempt)
            _tell(on_wait, f"{path}: {error}; trying again in {wait:g} s")
            logger.info("%s: %s; trying again in %g s", path, error, wait)
            sleep(wait)
            attempt += 1
            stats["retries"] = attempt
        except BaseException:
            progress.advance(-reported["bytes"])
            raise
    if not hub_checksum_ok(dest, entry):
        dest.unlink()
        progress.advance(-entry.get("size", 0))
        raise ChecksumMismatch(f"{path} does not match the Hub's checksum")
    progress.advance(0, item_done=True)
    return "fetched"


def _tell(callback: Callable[[str], None] | None, message: str) -> None:
    if callback:
        callback(message)


def fetch_files(
    client: HubClient,
    repo: str,
    commit: str,
    entries: list[dict],
    files_dir: Path,
    workers: int = DEFAULT_WORKERS,
    policy: RetryPolicy | None = None,
    sleep: Callable[[float], None] | None = None,
    on_wait: Callable[[str], None] | None = None,
    progress=None,
) -> FetchOutcome:
    """Fetch every entry; a file that fails is recorded and the others carry on."""
    policy = policy or RetryPolicy()
    sleep = sleep or time.sleep  # looked up now, so tests can replace the clock
    progress = progress or NullReporter()
    outcome = FetchOutcome()
    progress.start(
        f"Downloading {repo}",
        total_bytes=sum(e.get("size", 0) for e in entries),
        total_items=len(entries),
    )

    def work(entry: dict) -> tuple[dict, dict]:
        started = time.monotonic()
        stats = {"retries": 0}
        item = {"name": entry["path"], "size": entry.get("size"), "retries": 0}
        try:
            dest = fsutil.safe_join(files_dir, entry["path"])
            item["status"] = _fetch_one(
                client, repo, commit, entry, dest, policy, sleep, on_wait, progress, stats
            )
        except (HubError, ChecksumMismatch, fsutil.UnsafePathError, OSError) as error:
            item["status"], item["reason"] = "failed", str(error)
        item["retries"] = stats["retries"]
        item["seconds"] = round(time.monotonic() - started, 3)
        return entry, item

    with progress.running(), ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for entry, item in pool.map(work, entries):
            outcome.items.append(item)
            if item["status"] == "failed":
                outcome.failed.append({"path": entry["path"], "reason": item["reason"]})
                logger.warning("failed %s: %s", entry["path"], item["reason"])
            elif item["status"] == "skipped":
                outcome.skipped.append(entry["path"])
                logger.info("skipped %s (already fetched and checked)", entry["path"])
            else:
                outcome.fetched.append(entry["path"])
                logger.info(
                    "fetched %s (%s bytes in %s s, %d retries)",
                    entry["path"],
                    item["size"],
                    item["seconds"],
                    item["retries"],
                )
    progress.finish()
    return outcome
