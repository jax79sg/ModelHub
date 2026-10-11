"""Filtering, sorting, faceting and paging for the /models listing."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from . import fmt
from .store import Model

PAGE_SIZE = 30

SORTS = [
    ("downloads", "Most downloads"),
    ("likes", "Most likes"),
    ("modified", "Recently updated"),
    ("created", "Recently created"),
    ("name", "Name (A–Z)"),
]
SORT_KEYS = {k for k, _ in SORTS}
DISPLAYED = ("main", "tasks", "libraries", "languages", "licenses", "other")

# Tags that are plumbing rather than something a person filters by.
NOISE_PREFIXES = ("region:", "license:", "dataset:", "arxiv:", "doi:", "base_model:", "deploy:")
NOISE = {"endpoints_compatible", "text-embeddings-inference", "text-generation-inference", "autotrain_compatible"}


@dataclass
class Query:
    search: str = ""
    pipeline_tag: list[str] = field(default_factory=list)
    library: list[str] = field(default_factory=list)
    license: list[str] = field(default_factory=list)
    language: list[str] = field(default_factory=list)
    other: list[str] = field(default_factory=list)
    pmin: int = 0
    pmax: int = len(fmt.PARAM_LABELS) - 1
    sort: str = "downloads"
    page: int = 0
    displayed: str = "main"

    @property
    def params_active(self) -> bool:
        return self.pmin > 0 or self.pmax < len(fmt.PARAM_LABELS) - 1

    def clamp(self) -> Query:
        top = len(fmt.PARAM_LABELS) - 1
        self.pmin = max(0, min(self.pmin, top))
        self.pmax = max(self.pmin, min(self.pmax, top))
        if self.sort not in SORT_KEYS:
            self.sort = "downloads"
        if self.displayed not in DISPLAYED:
            self.displayed = "main"
        self.page = max(0, min(self.page, 100_000))
        self.search = self.search.strip()[:200]
        return self

    def params(self, **override) -> list[tuple[str, str]]:
        """Query-string pairs for a link that changes some fields. Defaults are omitted."""
        cur = {**self.__dict__, **override}
        out: list[tuple[str, str]] = []
        if cur["search"]:
            out.append(("search", cur["search"]))
        for key in ("pipeline_tag", "library", "license", "language", "other"):
            out += [(key, v) for v in cur[key]]
        top = len(fmt.PARAM_LABELS) - 1
        if cur["pmin"] > 0:
            out.append(("pmin", str(cur["pmin"])))
        if cur["pmax"] < top:
            out.append(("pmax", str(cur["pmax"])))
        if cur["sort"] != "downloads":
            out.append(("sort", cur["sort"]))
        if cur["displayed"] != "main":
            out.append(("displayed", cur["displayed"]))
        if cur["page"]:
            out.append(("p", str(cur["page"])))
        return out

    def toggled(self, key: str, value: str) -> list[tuple[str, str]]:
        values = list(getattr(self, key))
        values = [v for v in values if v != value] if value in values else values + [value]
        return self.params(**{key: values, "page": 0})


def facet_tags(model: Model) -> list[str]:
    return [t for t in model.tags if not t.startswith(NOISE_PREFIXES) and t not in NOISE]


def matches(model: Model, q: Query) -> bool:
    if q.search:
        needle = q.search.lower()
        if needle not in model.id.lower() and not any(needle in t.lower() for t in model.tags):
            return False
    if q.pipeline_tag and model.pipeline_tag not in q.pipeline_tag:
        return False
    if q.library and not (set(q.library) & ({model.library} | set(model.tags))):
        return False
    if q.license and model.license not in q.license:
        return False
    if q.language and not (set(q.language) & set(model.languages)):
        return False
    if q.other and not set(q.other) <= set(model.tags):
        return False
    if q.params_active:
        n = model.num_parameters
        if n is None or n < fmt.PARAM_LOWER[q.pmin] or n > fmt.PARAM_UPPER[q.pmax]:
            return False
    return True


def sort_models(models: list[Model], key: str) -> list[Model]:
    def stamp(value: str | None) -> float:
        dt = fmt.parse_time(value)
        return dt.timestamp() if dt else 0.0

    if key == "name":
        return sorted(models, key=lambda m: m.id.lower())
    if key == "likes":
        return sorted(models, key=lambda m: (-(m.likes or 0), m.id.lower()))
    if key == "modified":
        return sorted(models, key=lambda m: (-stamp(m.last_modified), m.id.lower()))
    if key == "created":
        return sorted(models, key=lambda m: (-stamp(m.created_at), m.id.lower()))
    return sorted(models, key=lambda m: (-(m.downloads or 0), m.id.lower()))


@dataclass
class Facet:
    value: str
    label: str
    count: int
    active: bool


@dataclass
class Result:
    models: list[Model]
    total: int
    all_total: int
    pages: int
    tasks: list[Facet]
    libraries: list[Facet]
    languages: list[Facet]
    licenses: list[Facet]
    others: list[Facet]


def _facets(counter: Counter, active: list[str], label) -> list[Facet]:
    items = [Facet(v, label(v), c, v in active) for v, c in counter.items()]
    # Active first so a selection never hides, then by popularity.
    return sorted(items, key=lambda f: (not f.active, -f.count, f.label.lower()))


def run(models: list[Model], q: Query) -> Result:
    hits = sort_models([m for m in models if matches(m, q)], q.sort)
    pages = max(1, -(-len(hits) // PAGE_SIZE))
    page = min(q.page, pages - 1)
    q.page = page

    tasks, libs, langs, lics, others = Counter(), Counter(), Counter(), Counter(), Counter()
    for m in models:  # facets describe the whole store so a selection can be widened again
        if m.pipeline_tag:
            tasks[m.pipeline_tag] += 1
        for lib in {m.library, *(t for t in m.tags if t in fmt.LIBRARIES)} - {None}:
            libs[lib] += 1
        for lang in set(m.languages):
            langs[lang] += 1
        if m.license:
            lics[m.license] += 1
        for t in facet_tags(m):
            if t not in fmt.LIBRARIES and t != m.pipeline_tag and t not in m.languages:
                others[t] += 1

    return Result(
        models=hits[page * PAGE_SIZE : (page + 1) * PAGE_SIZE],
        total=len(hits),
        all_total=len(models),
        pages=pages,
        tasks=_facets(tasks, q.pipeline_tag, fmt.pipeline_label),
        libraries=_facets(libs, q.library, fmt.library_label),
        languages=_facets(langs, q.language, fmt.language_label),
        licenses=_facets(lics, q.license, lambda v: v),
        others=_facets(others, q.other, lambda v: v),
    )
