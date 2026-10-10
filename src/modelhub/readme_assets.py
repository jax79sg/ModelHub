"""Pictures in a README that live on other websites (FR4).

The web app is offline, so such pictures are downloaded and a second README points to the
local copies. The original README is never changed. Fetching is deliberately plain: no login
or token is ever sent to these addresses (NFR6.1), only `http` and `https` are used, and each
picture is size- and time-limited (NFR5.3).
"""

from __future__ import annotations

import hashlib
import http.client
import posixpath
import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path

from modelhub import __version__
from modelhub.fsutil import atomic_write_bytes

MAX_PICTURE_BYTES = 7 * 1024 * 1024
PICTURE_TIMEOUT = 30  # seconds

_MARKDOWN_IMAGE = re.compile(r"(!\[[^\]]*\]\(\s*<?)([^)\s>]+)(>?(?:\s+\"[^\"]*\")?\s*\))")
_HTML_IMAGE = re.compile(r"(<img\b[^>]*?\bsrc\s*=\s*([\"']))(.*?)(\2)", re.IGNORECASE | re.DOTALL)


class PictureError(Exception):
    """A picture could not be fetched."""


class PictureTooLarge(PictureError):
    pass


Fetcher = Callable[[str, int, float], bytes]


def find_pictures(text: str) -> list[str]:
    """Every picture reference in a README, once each, in order of appearance."""
    found: list[tuple[int, str]] = []
    for match in _MARKDOWN_IMAGE.finditer(text):
        found.append((match.start(), match.group(2)))
    for match in _HTML_IMAGE.finditer(text):
        found.append((match.start(), match.group(3)))
    seen: list[str] = []
    for _, ref in sorted(found):
        if ref not in seen:
            seen.append(ref)
    return seen


def fetch_url(url: str, max_bytes: int, timeout: float) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": f"modelhub/{__version__}"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            length = response.headers.get("Content-Length")
            if length and length.isdigit() and int(length) > max_bytes:
                raise PictureTooLarge(f"larger than {max_bytes} bytes")
            data = response.read(max_bytes + 1)
    except PictureError:
        raise
    except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError) as error:
        raise PictureError(str(error)) from error
    if len(data) > max_bytes:
        raise PictureTooLarge(f"larger than {max_bytes} bytes")
    return data


def _local_name(url: str, data: bytes) -> str:
    base = posixpath.basename(urllib.parse.urlparse(url).path) or "picture"
    base = re.sub(r"[^A-Za-z0-9._-]", "_", urllib.parse.unquote(base))[-80:] or "picture"
    if "." not in base:
        base += ".img"
    return f"{hashlib.sha256(data).hexdigest()[:12]}-{base}"


def _scheme(ref: str) -> str:
    return urllib.parse.urlparse(ref).scheme.lower()


def process_readme(
    text: str,
    assets_dir: Path,
    fetcher: Fetcher = fetch_url,
    max_bytes: int = MAX_PICTURE_BYTES,
    timeout: float = PICTURE_TIMEOUT,
) -> tuple[str, list[dict]]:
    """Fetch outside pictures into `assets_dir` and return the rewritten README text and a
    record of what happened to each picture."""
    replacements: dict[str, str] = {}
    pictures: list[dict] = []
    for ref in find_pictures(text):
        scheme = _scheme(ref)
        if scheme == "" and not ref.startswith("//"):
            continue  # a picture stored in the repository: already among the fetched files
        if scheme not in ("http", "https"):
            pictures.append(
                {
                    "source": ref,
                    "local": None,
                    "status": "skipped",
                    "reason": "not an http or https address",
                }
            )
            continue
        try:
            data = fetcher(ref, max_bytes, timeout)
        except PictureTooLarge as error:
            pictures.append(
                {"source": ref, "local": None, "status": "skipped", "reason": str(error)}
            )
            continue
        except PictureError as error:
            pictures.append(
                {"source": ref, "local": None, "status": "failed", "reason": str(error)}
            )
            continue
        name = _local_name(ref, data)
        atomic_write_bytes(Path(assets_dir) / name, data)
        replacements[ref] = f"assets/{name}"
        pictures.append({"source": ref, "local": f"readme/assets/{name}", "status": "fetched"})

    def swap_markdown(match: re.Match) -> str:
        return match.group(1) + replacements.get(match.group(2), match.group(2)) + match.group(3)

    def swap_html(match: re.Match) -> str:
        return match.group(1) + replacements.get(match.group(3), match.group(3)) + match.group(4)

    rewritten = _MARKDOWN_IMAGE.sub(swap_markdown, text)
    rewritten = _HTML_IMAGE.sub(swap_html, rewritten)
    return rewritten, pictures
