"""Render a model card (README) to safe HTML.

A README is untrusted text from the internet, so the output is sanitised with an
allow-list and nothing in it can load a remote resource: remote images are
replaced by their alt text, scripts, styles, forms and event handlers are dropped.
"""

from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass
from urllib.parse import quote, urlsplit

import nh3
from markdown_it import MarkdownIt
from mdit_py_plugins.anchors import anchors_plugin

FRONT_MATTER = re.compile(r"\A﻿?---\s*\n.*?\n(?:---|\.\.\.)\s*(?:\n|\Z)", re.S)

ALLOWED_TAGS = {
    "a",
    "abbr",
    "b",
    "blockquote",
    "br",
    "code",
    "dd",
    "del",
    "details",
    "div",
    "dl",
    "dt",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "i",
    "img",
    "kbd",
    "li",
    "ol",
    "p",
    "pre",
    "s",
    "span",
    "strong",
    "sub",
    "summary",
    "sup",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "tr",
    "ul",
    "figure",
    "figcaption",
    "picture",
    "center",
}
ALLOWED_ATTRS = {
    "*": {"align", "title"},
    "a": {"href", "name"},
    "img": {"src", "alt", "width", "height"},
    "td": {"colspan", "rowspan", "align"},
    "th": {"colspan", "rowspan", "align"},
    "ol": {"start"},
    "details": {"open"},
    "code": {"class"},
    **{f"h{i}": {"id"} for i in range(1, 7)},
}
SAFE_CLASS = re.compile(r"^language-[A-Za-z0-9_+-]{1,30}$")


@dataclass
class Rendered:
    html: str
    toc: list[tuple[int, str, str]]  # (level, id, title)


def strip_front_matter(text: str) -> str:
    return FRONT_MATTER.sub("", text, count=1)


def _slug(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    return re.sub(r"[\s_]+", "-", s) or "section"


def _md() -> MarkdownIt:
    md = MarkdownIt("commonmark", {"html": True, "breaks": False}).enable(["table", "strikethrough"])
    md.use(anchors_plugin, min_level=1, max_level=4, slug_func=_slug, permalink=False)
    return md


_MD = _md()


def render(text: str, model_id: str, commit: str, rev: str) -> Rendered:
    """``rev`` is the revision used in links (a ref name or commit), ``commit`` the stored commit."""
    body = strip_front_matter(text)
    tokens = _MD.parse(body)
    toc: list[tuple[int, str, str]] = []
    for i, tok in enumerate(tokens):
        if tok.type == "heading_open" and tok.tag in ("h1", "h2", "h3", "h4"):
            title = tokens[i + 1].content if i + 1 < len(tokens) else ""
            toc.append((int(tok.tag[1]), tok.attrGet("id") or "", title))
    raw = _MD.renderer.render(tokens, _MD.options, {})

    base = f"/{model_id}"

    def fix_attr(tag: str, attr: str, value: str) -> str | None:
        if tag == "code" and attr == "class":
            return value if SAFE_CLASS.match(value) else None
        if tag == "img" and attr == "src":
            return _local_src(value, base, commit)
        if tag == "a" and attr == "href":
            return _href(value, base, rev)
        return value

    clean = nh3.clean(
        raw,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        attribute_filter=fix_attr,
        url_schemes={"http", "https", "mailto"},
        link_rel="noopener noreferrer nofollow",
        strip_comments=True,
    )
    clean = _drop_remote_images(clean)
    return Rendered(clean, toc)


def _is_remote(url: str) -> bool:
    parts = urlsplit(url)
    return bool(parts.scheme or parts.netloc or url.startswith("//"))


def _local_src(value: str, base: str, commit: str) -> str | None:
    if _is_remote(value):
        return None  # removed; _drop_remote_images swaps the tag for its alt text
    path = posixpath.normpath(urlsplit(value).path)
    if path.startswith("/") or path.startswith(".."):
        return None
    return f"{base}/readme-asset/{commit}/{quote(path)}"


def _href(value: str, base: str, rev: str) -> str | None:
    parts = urlsplit(value)
    if parts.scheme or parts.netloc:
        return value if parts.scheme in ("http", "https", "mailto") else None
    if value.startswith("#"):
        return value
    path = posixpath.normpath(parts.path)
    if not path or path.startswith("/") or path.startswith(".."):
        return None
    return f"{base}/blob/{quote(rev, safe='')}/{quote(path)}"


_IMG_TAG = re.compile(r"<img\b[^>]*>", re.I)
_ALT = re.compile(r'\salt="([^"]*)"')


def _drop_remote_images(html: str) -> str:
    """nh3 removed the src of remote images; show their alt text instead of a broken picture."""

    def repl(m: re.Match) -> str:
        tag = m.group(0)
        if re.search(r"\ssrc=", tag):
            return tag
        alt = _ALT.search(tag)
        label = (alt.group(1) if alt else "") or "image"
        return f'<span class="md-missing-image" title="Remote image not available offline">[{label}]</span>'

    return _IMG_TAG.sub(repl, html)
