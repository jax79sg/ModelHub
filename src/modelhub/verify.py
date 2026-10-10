"""`verify`: check a bundle's signature and every piece, naming everything wrong in one run."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from modelhub import fsutil, record, signing
from modelhub import store as store_mod
from modelhub.progress import NullReporter

logger = logging.getLogger("modelhub.verify")


@dataclass
class Problem:
    code: str
    message: str
    piece: str | None = None


@dataclass
class BundleReport:
    stem: str
    manifest: dict | None = None
    manifest_bytes: bytes = b""
    piece_paths: list[Path] = field(default_factory=list)
    problems: list[Problem] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems


class VerifyFailed(Exception):
    def __init__(self, reports: list[BundleReport]):
        lines = [f"{r.stem}: {p.message}" for r in reports for p in r.problems]
        super().__init__("; ".join(lines) or "verification failed")
        self.reports = reports


def _find_manifests(dirs: list[Path]) -> dict[str, list[Path]]:
    found: dict[str, list[Path]] = {}
    for directory in dirs:
        for path in sorted(Path(directory).glob("*.bundle.json")):
            found.setdefault(path.name[: -len(".bundle.json")], []).append(path)
    return found


def _pick_final(paths: list[Path]) -> Path | None:
    for path in paths:
        try:
            if json.loads(path.read_text(encoding="utf-8")).get("complete"):
                return path
        except (OSError, ValueError):
            continue
    return None


def _check_signature(report: BundleReport, manifest_path: Path) -> None:
    sig_path = manifest_path.with_name(manifest_path.name[: -len(".json")] + ".sig")
    sig_doc = None
    if sig_path.is_file():
        try:
            sig_doc = json.loads(sig_path.read_text(encoding="utf-8"))
        except ValueError:
            sig_doc = {}
    try:
        signing.verify_signature(sig_doc, report.manifest_bytes)
    except signing.SignatureProblem as problem:
        report.problems.append(Problem(problem.code, str(problem)))


def _check_pieces(report: BundleReport, dirs: list[Path], progress) -> None:
    progress.start(
        f"Checking {report.stem}",
        total_bytes=sum(piece["size"] for piece in report.manifest.get("pieces", [])),
    )
    for piece in report.manifest.get("pieces", []):
        located = next(
            (Path(d) / piece["name"] for d in dirs if (Path(d) / piece["name"]).is_file()), None
        )
        if located is None:
            report.problems.append(
                Problem("piece-missing", f"missing piece {piece['name']}", piece["name"])
            )
            continue
        if (
            located.stat().st_size != piece["size"]
            or fsutil.sha256_file(located, on_block=progress.advance) != piece["sha256"]
        ):
            report.problems.append(
                Problem("piece-damaged", f"damaged piece {piece['name']}", piece["name"])
            )
        report.piece_paths.append(located)


def verify_bundle(dirs: list[Path], progress=None) -> list[BundleReport]:
    dirs = [Path(d) for d in dirs]
    progress = progress or NullReporter()
    reports = []
    for stem, paths in sorted(_find_manifests(dirs).items()):
        report = BundleReport(stem)
        reports.append(report)
        final = _pick_final(paths)
        if final is None:
            report.problems.append(
                Problem(
                    "incomplete-bundle",
                    "no finished manifest found; the last drive's manifest is missing",
                )
            )
            continue
        report.manifest_bytes = final.read_bytes()
        # The signature comes first: nothing in a manifest is acted on until it is proved genuine.
        _check_signature(report, final)
        if report.problems:
            continue
        try:
            report.manifest = json.loads(report.manifest_bytes)
            record.check_format_version(report.manifest.get("format_version", "0"))
            with progress.running():
                _check_pieces(report, dirs, progress)
        except record.UnsupportedFormat as error:
            report.problems.append(Problem("unsupported-format", str(error)))
        except (ValueError, KeyError, TypeError, AttributeError):
            report.problems.append(Problem("manifest-malformed", "the manifest is not readable"))
        for problem in report.problems:
            logger.info("%s: %s", stem, problem.message)
    progress.finish()
    return reports


def verify_store(store_dir: Path) -> list[Problem]:
    """Check every file of every version in a model store against its manifest."""
    problems: list[Problem] = []
    for item in store_mod.list_models(Path(store_dir)):
        root = store_mod.StorePaths(Path(store_dir), item.model_id).commit_dir(item.commit)
        label = f"{item.model_id} {item.commit[:12]}"
        try:
            manifest = record.load_manifest(root / "manifest.json")
        except (OSError, ValueError, record.UnsupportedFormat) as error:
            problems.append(Problem("manifest-unreadable", f"{label}: manifest.json: {error}"))
            continue
        for entry in manifest["files"]:
            path = root / "files" / entry["path"]
            if not path.is_file():
                problems.append(Problem("file-missing", f"{label}: missing file {entry['path']}"))
            elif (
                path.stat().st_size != entry["size"] or fsutil.sha256_file(path) != entry["sha256"]
            ):
                problems.append(Problem("file-damaged", f"{label}: damaged file {entry['path']}"))
    return problems
