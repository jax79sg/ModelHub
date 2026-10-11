"""Read-only access to a modelhub model store (contract C3).

Layout read::

    <store>/models/<org>/<name>/latest              commit id (text)
    <store>/models/<org>/<name>/refs/<ref name>     commit id (text)
    <store>/models/<org>/<name>/commits/<commit>/   summary.json, manifest.json,
                                                    files/, raw/, readme/

Everything here is defensive: Hugging Face fields that were not captured are
``None``, and a damaged or half-written model is skipped rather than crashing
the site.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
COMMIT = re.compile(r"^[0-9a-f]{7,64}$")
HIDDEN_TOP = ".modelhub-dl"


def valid_model_id(model_id: str) -> bool:
    parts = model_id.split("/")
    return len(parts) == 2 and all(SEGMENT.match(p) and p not in (".", "..") for p in parts)


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def as_list(value: Any) -> list[str]:
    """Normalise a field that Hugging Face sometimes gives as str, list or null."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value if v is not None]
    return [str(value)]


@dataclass
class FileEntry:
    path: str
    type: str  # "file" | "directory"
    size: int
    in_store: bool
    sha256: str | None = None
    kind: str | None = None  # modelhub file-type group (safetensors, settings, ...)
    last_commit: dict | None = None
    scan: dict | None = None

    @property
    def name(self) -> str:
        return self.path.rsplit("/", 1)[-1]


@dataclass
class Model:
    id: str
    root: Path
    latest: str | None
    refs: dict[str, str]
    commits: list[str]
    summary: dict = field(default_factory=dict)

    # ----- convenience accessors over the latest summary.json -----
    @property
    def card(self) -> dict:
        return self.summary.get("card") or {}

    @property
    def stats(self) -> dict:
        return self.summary.get("stats") or {}

    @property
    def org(self) -> str | None:
        return self.id.split("/")[0] if "/" in self.id else None

    @property
    def short_name(self) -> str:
        return self.id.split("/")[-1]

    @property
    def pipeline_tag(self) -> str | None:
        return self.card.get("pipeline_tag")

    @property
    def library(self) -> str | None:
        return self.card.get("library_name")

    @property
    def tags(self) -> list[str]:
        return as_list(self.card.get("tags"))

    @property
    def languages(self) -> list[str]:
        return as_list(self.card.get("language"))

    @property
    def license(self) -> str | None:
        lic = as_list(self.card.get("license")) or as_list((self.summary.get("license") or {}).get("name"))
        return lic[0] if lic else None

    @property
    def downloads(self) -> int | None:
        return self.stats.get("downloads")

    @property
    def likes(self) -> int | None:
        return self.stats.get("likes")

    @property
    def num_parameters(self) -> int | None:
        pc = self.stats.get("parameter_counts")
        total = pc.get("total") if isinstance(pc, dict) else None
        return total if isinstance(total, int) else None

    @property
    def last_modified(self) -> str | None:
        return self.summary.get("last_modified")

    @property
    def created_at(self) -> str | None:
        return self.summary.get("created_at")

    @property
    def captured_at(self) -> str | None:
        return self.summary.get("captured_at")

    # ----- revisions -----
    def resolve(self, rev: str) -> str | None:
        """Turn a ref name, ``latest`` or a (prefix of a) commit id into a captured commit."""
        if rev in ("latest",):
            return self.latest
        if rev in self.refs and self.refs[rev] in self.commits:
            return self.refs[rev]
        if COMMIT.match(rev):
            hits = [c for c in self.commits if c.startswith(rev)]
            if len(hits) == 1:
                return hits[0]
        return None

    def commit_dir(self, commit: str) -> Path:
        return self.root / "commits" / commit

    def summary_for(self, commit: str) -> dict:
        if commit == self.latest:
            return self.summary
        return _read_json(self.commit_dir(commit) / "summary.json") or {}

    def ref_names_for(self, commit: str) -> list[str]:
        return sorted(n for n, c in self.refs.items() if c == commit)

    # ----- files -----
    def entries(self, commit: str) -> list[FileEntry]:
        """Every file Hugging Face lists for this commit, flagged by whether it was downloaded."""
        cdir = self.commit_dir(commit)
        summary = self.summary_for(commit)
        stored = {
            f["path"]: f
            for f in summary.get("files") or []
            if isinstance(f, dict) and f.get("path") and not f["path"].startswith(HIDDEN_TOP)
        }
        tree = _read_json(cdir / "raw" / "tree.json")
        out: dict[str, FileEntry] = {}
        if isinstance(tree, list):
            for t in tree:
                if not isinstance(t, dict) or not t.get("path") or t["path"].startswith(HIDDEN_TOP):
                    continue
                p = t["path"]
                s = stored.get(p)
                out[p] = FileEntry(
                    path=p,
                    type="directory" if t.get("type") == "directory" else "file",
                    size=int(t.get("size") or 0),
                    in_store=s is not None,
                    sha256=(s or {}).get("sha256"),
                    kind=(s or {}).get("type"),
                    last_commit=t.get("lastCommit"),
                    scan=(s or {}).get("scan") or t.get("securityFileStatus"),
                )
        for p, s in stored.items():  # files the tree listing did not mention
            out.setdefault(
                p,
                FileEntry(p, "file", int(s.get("size") or 0), True, s.get("sha256"), s.get("type"), None, s.get("scan")),
            )
        return list(out.values())

    def listing(self, commit: str, folder: str) -> list[FileEntry] | None:
        """Direct children of ``folder`` (``""`` for the top). None if the folder does not exist."""
        entries = self.entries(commit)
        prefix = f"{folder}/" if folder else ""
        children: dict[str, FileEntry] = {}
        dir_info = {e.path: e for e in entries if e.type == "directory"}
        known_folder = folder == "" or folder in dir_info or any(e.path.startswith(prefix) for e in entries)
        if not known_folder:
            return None
        for e in entries:
            if not e.path.startswith(prefix) or e.type == "directory" and e.path == folder:
                continue
            rest = e.path[len(prefix) :]
            if not rest:
                continue
            head = rest.split("/", 1)[0]
            child_path = prefix + head
            if "/" in rest:  # nested: make sure the directory shows up
                children.setdefault(
                    child_path,
                    dir_info.get(child_path) or FileEntry(child_path, "directory", 0, True),
                )
            else:
                children[child_path] = e
        return sorted(children.values(), key=lambda e: (e.type != "directory", e.name.lower()))

    def find_file(self, commit: str, path: str) -> FileEntry | None:
        for e in self.entries(commit):
            if e.type == "file" and e.path == path:
                return e
        return None

    def file_path(self, commit: str, path: str) -> Path | None:
        """Absolute path of a stored file, or None. Refuses anything outside ``files/``."""
        entry = self.find_file(commit, path)
        if entry is None or not entry.in_store:
            return None
        base = (self.commit_dir(commit) / "files").resolve()
        target = (base / path).resolve()
        if base not in target.parents or not target.is_file():
            return None
        return target

    def asset_path(self, commit: str, rel: str) -> Path | None:
        """A README picture under ``readme/``. Refuses anything outside it."""
        base = (self.commit_dir(commit) / "readme").resolve()
        target = (base / rel).resolve()
        if base not in target.parents or not target.is_file():
            return None
        return target

    def readme_text(self, commit: str) -> tuple[str, bool] | None:
        """(markdown, uses_local_pictures). Prefers the local copy so pictures work offline."""
        summary = self.summary_for(commit)
        info = summary.get("readme") or {}
        cdir = self.commit_dir(commit)
        for key, local in (("local", True), ("original", False)):
            rel = info.get(key)
            if not rel:
                continue
            target = (cdir / rel).resolve()
            if cdir.resolve() in target.parents and target.is_file():
                try:
                    return target.read_text(encoding="utf-8", errors="replace"), local
                except OSError:
                    continue
        return None

    def history(self, commit: str) -> list[dict]:
        data = _read_json(self.commit_dir(commit) / "raw" / "commits.json")
        return [c for c in data if isinstance(c, dict)] if isinstance(data, list) else []

    def raw_refs(self, commit: str) -> dict:
        data = _read_json(self.commit_dir(commit) / "raw" / "refs.json")
        return data if isinstance(data, dict) else {}


class Store:
    def __init__(self, root: Path):
        self.root = Path(root)
        self._cache: dict[str, Model] = {}
        self._stamp: tuple | None = None

    @property
    def models_dir(self) -> Path:
        return self.root / "models"

    def _model_dirs(self) -> list[tuple[str, Path]]:
        found = []
        base = self.models_dir
        if not base.is_dir():
            return found
        for first in sorted(base.iterdir()):
            if not first.is_dir() or not SEGMENT.match(first.name):
                continue
            for second in sorted(first.iterdir()):
                if second.is_dir() and SEGMENT.match(second.name) and (second / "commits").is_dir():
                    found.append((f"{first.name}/{second.name}", second))
        return found

    def _fingerprint(self, dirs: list[tuple[str, Path]]) -> tuple:
        sig = []
        for mid, d in dirs:
            latest = d / "latest"
            try:
                sig.append((mid, latest.stat().st_mtime_ns, len(list((d / "commits").iterdir()))))
            except OSError:
                sig.append((mid, 0, 0))
        return tuple(sig)

    def _load(self, model_id: str, root: Path) -> Model | None:
        latest = _read_text(root / "latest")
        commits = sorted(p.name for p in (root / "commits").iterdir() if p.is_dir() and (p / "summary.json").is_file())
        if not commits:
            return None
        if latest not in commits:
            latest = commits[-1]
        refs: dict[str, str] = {}
        refs_dir = root / "refs"
        if refs_dir.is_dir():
            for f in refs_dir.rglob("*"):
                if f.is_file():
                    val = _read_text(f)
                    if val:
                        refs[f.relative_to(refs_dir).as_posix()] = val
        summary = _read_json(root / "commits" / latest / "summary.json")
        if not isinstance(summary, dict):
            return None
        return Model(model_id, root, latest, refs, commits, summary)

    def models(self) -> list[Model]:
        dirs = self._model_dirs()
        stamp = self._fingerprint(dirs)
        if stamp != self._stamp:
            self._cache = {}
            for mid, root in dirs:
                m = self._load(mid, root)
                if m is not None:
                    self._cache[mid] = m
            self._stamp = stamp
        return list(self._cache.values())

    def get(self, model_id: str) -> Model | None:
        if not valid_model_id(model_id):
            return None
        self.models()
        return self._cache.get(model_id)
