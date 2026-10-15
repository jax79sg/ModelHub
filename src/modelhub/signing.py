"""Signing keys, fingerprints and trust (NFR2.3 to NFR2.9).

The download side keeps a private key and signs each bundle's manifest. The air-gapped side
trusts a public key only after a person types its fingerprint, received by a separate route.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from modelhub.fsutil import atomic_write_bytes, atomic_write_text

FORMAT_VERSION = "1.0"
ALGORITHM = "ed25519"


class KeyError_(Exception):
    """Something is wrong with a key or its handling."""


class NoSigningKey(KeyError_):
    """There is no private key on this computer to sign with: the command cannot run."""


class SignatureProblem(Exception):
    """A bundle's signature is missing, invalid, or from a key this side does not trust."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def home() -> Path:
    return Path(os.environ.get("MODELHUB_HOME") or Path.home() / ".modelhub")


def _keys_dir() -> Path:
    return home() / "keys"


def _trusted_dir() -> Path:
    return home() / "trusted"


def fingerprint_of(public_raw: bytes) -> str:
    """A short, readable fingerprint a person can compare on both sides."""
    digest = hashlib.sha256(public_raw).hexdigest()[:32]
    return "-".join(digest[i : i + 4] for i in range(0, 32, 4))


def _key_id(public_raw: bytes) -> str:
    return hashlib.sha256(public_raw).hexdigest()[:16]


def _normalize(fingerprint: str) -> str:
    return "".join(ch for ch in fingerprint.lower() if ch in "0123456789abcdef")


def _public_raw(private: Ed25519PrivateKey) -> bytes:
    return private.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )


def _public_doc(name: str, public_raw: bytes) -> dict:
    return {
        "format_version": FORMAT_VERSION,
        "type": "modelhub-public-key",
        "algorithm": ALGORITHM,
        "name": name,
        "key_id": _key_id(public_raw),
        "fingerprint": fingerprint_of(public_raw),
        "public_key": base64.b64encode(public_raw).decode("ascii"),
    }


def restrict_to_owner(path: Path) -> None:
    """Only the owner may read the private key file (NFR2.5)."""
    if sys.platform == "win32":  # pragma: no cover - exercised by the Windows checks
        user = os.environ.get("USERNAME", "")
        subprocess.run(
            ["icacls", str(path), "/inheritance:r", "/grant:r", f"{user}:F"],
            check=True,
            capture_output=True,
        )
    else:
        os.chmod(path, 0o600)


def create_key(name: str) -> dict:
    private = Ed25519PrivateKey.generate()
    public_raw = _public_raw(private)
    doc = _public_doc(name, public_raw)
    keys = _keys_dir()
    keys.mkdir(parents=True, exist_ok=True)
    key_path = keys / f"{doc['key_id']}.key"
    pem = private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    atomic_write_bytes(key_path, pem)
    restrict_to_owner(key_path)
    atomic_write_text(keys / f"{doc['key_id']}.pub.json", json.dumps(doc, indent=2) + "\n")
    return doc


def list_keys() -> list[dict]:
    keys = _keys_dir()
    if not keys.is_dir():
        return []
    return [json.loads(p.read_text()) for p in sorted(keys.glob("*.pub.json"))]


def default_key_id() -> str:
    keys = list_keys()
    if len(keys) == 1:
        return keys[0]["key_id"]
    if not keys:
        raise NoSigningKey("no signing key found; create one with 'modelhub key create'")
    raise KeyError_("more than one signing key exists; choose one with --key")


MIN_KEY_TEXT = 4  # the fewest characters of a key's id or fingerprint accepted as its name


def _find_key(text: str, keys: list[dict], whose: str) -> dict:
    """Pick one key from `keys` by what a person typed: its id, its fingerprint (dashes, spaces
    and capitals do not matter), or the first few characters of either. The key id is the start
    of the fingerprint, so one rule covers all of them."""
    typed = _normalize(text) if re.fullmatch(r"[0-9a-fA-F\s:\-]+", text.strip() or "x") else ""
    found = (
        [k for k in keys if _normalize(k["fingerprint"]).startswith(typed)]
        if len(typed) >= MIN_KEY_TEXT
        else []
    )
    if len(found) == 1:
        return found[0]
    if len(found) > 1:
        raise KeyError_(f"more than one key starts with {text!r}; type more of its id")
    if not keys:
        raise KeyError_(f"there is no key {whose}; make one with 'modelhub key create'")
    known = "; ".join(f"{k['key_id']} (fingerprint {k['fingerprint']}, {k['name']})" for k in keys)
    raise KeyError_(
        f"no key matches {text!r}. Keys {whose}: {known}. "
        "Use the key id or fingerprint, as shown by 'modelhub key list'."
    )


def find_own_key(text: str) -> dict:
    """A key made on this computer, named by id, fingerprint or the start of either."""
    return _find_key(text, list_keys(), "made on this computer")


def find_trusted_key(text: str) -> dict:
    """A key this computer trusts, named the same ways."""
    return _find_key(text, trusted_keys(), "trusted on this computer")


def export_public(key_id: str, out: Path) -> dict:
    doc = find_own_key(key_id)
    atomic_write_text(out, json.dumps(doc, indent=2) + "\n")
    return doc


def read_public_doc(path: Path) -> dict:
    """Read a public key file and check its fingerprint matches its key bytes."""
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        public_raw = base64.b64decode(doc["public_key"])
    except (OSError, ValueError, KeyError) as error:
        raise KeyError_(f"{path} is not a public key file") from error
    if doc.get("type") != "modelhub-public-key" or doc.get("algorithm") != ALGORITHM:
        raise KeyError_(f"{path} is not a modelhub public key")
    if doc.get("fingerprint") != fingerprint_of(public_raw) or doc.get("key_id") != _key_id(
        public_raw
    ):
        raise KeyError_(f"{path} has a fingerprint that does not match its key")
    return doc


def trust_key(doc: dict, typed_fingerprint: str) -> None:
    """Trust a public key only when the person typed its fingerprint correctly (NFR2.7)."""
    if _normalize(typed_fingerprint) != _normalize(doc["fingerprint"]):
        raise KeyError_("the fingerprint you typed does not match this key; it was not trusted")
    trusted = _trusted_dir()
    trusted.mkdir(parents=True, exist_ok=True)
    atomic_write_text(trusted / f"{doc['key_id']}.pub.json", json.dumps(doc, indent=2) + "\n")


def untrust_key(key_id: str) -> bool:
    try:
        key_id = find_trusted_key(key_id)["key_id"]
    except KeyError_:
        return False
    target = _trusted_dir() / f"{key_id}.pub.json"
    if target.is_file():
        target.unlink()
        return True
    return False


def trusted_keys() -> list[dict]:
    trusted = _trusted_dir()
    if not trusted.is_dir():
        return []
    return [json.loads(p.read_text()) for p in sorted(trusted.glob("*.pub.json"))]


def sign_bytes(key_id: str, data: bytes) -> dict:
    key_path = _keys_dir() / f"{key_id}.key"
    if not key_path.is_file():
        raise KeyError_(f"no private key named {key_id} on this computer")
    private = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
    public_doc = json.loads((_keys_dir() / f"{key_id}.pub.json").read_text())
    return {
        "format_version": FORMAT_VERSION,
        "algorithm": ALGORITHM,
        "key_id": key_id,
        "fingerprint": public_doc["fingerprint"],
        "signature": base64.b64encode(private.sign(data)).decode("ascii"),
    }


def verify_signature(sig_doc: dict | None, data: bytes, trusted: list[dict] | None = None) -> dict:
    """Return the trusted key's file if `data` carries a valid signature from it; otherwise say
    exactly why not. Fails closed (NFR2.4).

    `trusted` is a list of public key documents to trust instead of the keys kept on this
    computer; the import service passes its own list (an empty list trusts nothing)."""
    if not sig_doc:
        raise SignatureProblem("signature-missing", "the bundle has no signature file")
    key_id = sig_doc.get("key_id", "")
    trusted = {k["key_id"]: k for k in (trusted_keys() if trusted is None else trusted)}
    if key_id not in trusted:
        raise SignatureProblem(
            "key-untrusted",
            f"the bundle is signed by key {key_id} ({sig_doc.get('fingerprint', '?')}), "
            "which this computer does not trust; trust it with 'modelhub key trust'",
        )
    public = Ed25519PublicKey.from_public_bytes(base64.b64decode(trusted[key_id]["public_key"]))
    try:
        public.verify(base64.b64decode(sig_doc["signature"]), data)
    except (InvalidSignature, ValueError, KeyError) as error:
        raise SignatureProblem(
            "signature-invalid", "the signature does not match the manifest"
        ) from error
    return trusted[key_id]
