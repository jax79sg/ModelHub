"""`pull`: fetch one model into a download record (contract C1)."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from modelhub import download, filetypes, fsutil, readme_assets, record, summary
from modelhub.hubclient import HubClient, UnsupportedModel

logger = logging.getLogger("modelhub.pull")


class PullIncomplete(Exception):
    """Some files could not be fetched. The ones that were fetched are kept, so running the
    same command again fetches only what is missing (FR5.3)."""

    def __init__(self, model_id: str, failed: list[dict], items: list[dict] | None = None):
        names = ", ".join(f["path"] for f in failed)
        super().__init__(f"{model_id}: {len(failed)} file(s) could not be fetched: {names}")
        self.model_id = model_id
        self.failed = failed
        self.items = items or []


@dataclass
class PullResult:
    model_id: str
    commit: str
    record_dir: Path | None
    fetched: list[str] = field(default_factory=list)
    groups: list[filetypes.TypeGroup] = field(default_factory=list)
    nothing_matched: bool = False
    pictures_failed: int = 0
    name_warnings: list[str] = field(default_factory=list)
    items: list[dict] = field(default_factory=list)  # one per file and picture, for the run record


def pull_model(
    client: HubClient,
    repo_id: str,
    work: Path,
    revision: str = "main",
    selection: set[str] | None = None,
    now=record.utc_now,
    workers: int = download.DEFAULT_WORKERS,
    policy: download.RetryPolicy | None = None,
    sleep: Callable[[float], None] | None = None,
    on_wait: Callable[[str], None] | None = None,
    progress=None,
) -> PullResult:
    """Fetch the selected file types. With no selection nothing is downloaded and the types
    found are returned, so the person can choose (FR2.3)."""
    info = client.model_info(repo_id, revision)
    if info.get("private") or info.get("gated"):
        raise UnsupportedModel(
            f"{repo_id} is private or gated, which this version does not support"
        )
    model_id, commit = info["id"], info["sha"]
    tree = client.tree(model_id, commit)
    files = [entry for entry in tree if entry.get("type") == "file"]
    groups = filetypes.group_files(files)
    logger.info("%s: commit %s, %d files in the repository", model_id, commit[:12], len(files))
    logger.debug("%s: selection %s", model_id, sorted(selection) if selection else "none")
    if selection is None:
        return PullResult(model_id, commit, None, groups=groups)
    chosen = filetypes.choose(files, selection)  # refuses an unknown type before any download
    if not filetypes.selected_weight_files(files, selection) and "all" not in selection:
        return PullResult(model_id, commit, None, groups=groups, nothing_matched=True)

    paths = record.RecordPaths(Path(work), model_id, commit)
    with fsutil.RunLock(paths.root):
        paths.raw.mkdir(parents=True, exist_ok=True)
        for name, payload in (
            ("model_info.json", info),
            ("tree.json", tree),
            ("commits.json", client.commits(model_id, commit)),
            ("refs.json", client.refs(model_id)),
        ):
            fsutil.atomic_write_text(paths.raw / name, json.dumps(payload, indent=2) + "\n")

        # Names Windows cannot hold are reported by name, never renamed (FR6.8): on a Windows
        # computer they cannot be written, so they fail; elsewhere they are kept with a warning.
        awkward = {e["path"]: fsutil.windows_name_problems(e["path"]) for e in chosen}
        awkward = {path: why for path, why in awkward.items() if why}
        unwritable = [
            {"path": path, "reason": "cannot be written on Windows: " + "; ".join(why)}
            for path, why in awkward.items()
            if fsutil.IS_WINDOWS
        ]
        to_fetch = [e for e in chosen if not (fsutil.IS_WINDOWS and e["path"] in awkward)]

        outcome = download.fetch_files(
            client,
            model_id,
            commit,
            to_fetch,
            paths.files,
            workers=workers,
            policy=policy,
            sleep=sleep,
            on_wait=on_wait,
            progress=progress,
        )
        unwritable_items = [
            {"name": f["path"], "status": "failed", "reason": f["reason"]} for f in unwritable
        ]
        if outcome.failed or unwritable:
            raise PullIncomplete(
                model_id, outcome.failed + unwritable, outcome.items + unwritable_items
            )
        result = PullResult(model_id, commit, paths.root, outcome.fetched, groups)
        result.name_warnings = sorted(awkward)
        result.items = list(outcome.items)

        readme_local, pictures = _process_readme(paths)
        result.pictures_failed = sum(1 for p in pictures if p["status"] == "failed")
        result.items += [
            {"name": p["source"], "status": f"picture-{p['status']}", "reason": p.get("reason")}
            for p in pictures
        ]

        captured_at = now()
        by_path = {entry["path"]: entry for entry in files}
        manifest = record.new_manifest(
            model_id,
            commit,
            revision,
            record.build_file_entries(paths.files, by_path),
            captured_at,
        )
        record.write_manifest(paths, manifest)
        fsutil.atomic_write_text(
            paths.summary,
            json.dumps(
                summary.build_summary(info, manifest, captured_at, readme_local, pictures),
                indent=2,
            )
            + "\n",
        )
    return result


def _process_readme(paths: record.RecordPaths) -> tuple[str | None, list[dict]]:
    """Make the second README with local pictures; the original stays unchanged (FR4.2)."""
    original = paths.files / "README.md"
    if not original.is_file():
        return None, []
    # Read as bytes, not text: reading as text would turn Windows line endings into plain ones.
    text = original.read_bytes().decode("utf-8", errors="surrogateescape")
    rewritten, pictures = readme_assets.process_readme(text, paths.readme / "assets")
    fsutil.atomic_write_bytes(
        paths.readme / "README.local.md", rewritten.encode("utf-8", errors="surrogateescape")
    )
    return "readme/README.local.md", pictures
