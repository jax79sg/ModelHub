"""The server address and personal token, saved by ``login`` for this person only (BR1.1, BR1.2)."""

from __future__ import annotations

import json
import os
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from modelhub.record import utc_now

FILE_NAME = "settings.json"
LOCAL_HOSTS = {"localhost", "127.0.0.1"}


class SettingsError(ValueError):
    """Settings are missing, not usable, or could not be saved safely. Exit status 2."""


@dataclass
class ClientSettings:
    server: str
    token: str

    def __repr__(self) -> str:  # never show the token, even by accident
        return f"ClientSettings(server={self.server!r}, token='[hidden]')"


def settings_dir() -> Path:
    override = os.environ.get("MODELHUB_CONFIG_DIR")
    if override:
        return Path(override)
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "modelhub"
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "modelhub"


def settings_path() -> Path:
    return settings_dir() / FILE_NAME


def check_address(address: str) -> str:
    """The address cleaned up, or a SettingsError saying why it cannot be used."""
    address = (address or "").strip().rstrip("/")
    parts = urlsplit(address)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise SettingsError("The server address must look like https://modelhub.example.org")
    if parts.scheme == "http" and parts.hostname not in LOCAL_HOSTS:
        raise SettingsError(
            "The server address must start with https:// (http:// is allowed only for "
            "localhost and 127.0.0.1)."
        )
    if parts.username or parts.password or parts.query or parts.fragment:
        raise SettingsError("The server address must not hold a name, password, query or fragment.")
    return address


def save(server: str, token: str) -> Path:
    """Write the settings readable by this person only; save nothing if that cannot be made so."""
    server = check_address(server)
    token = (token or "").strip()
    if not token:
        raise SettingsError("The token is empty.")
    folder = settings_dir()
    path = folder / FILE_NAME
    document = json.dumps({"server": server, "token": token, "saved_at": utc_now()}) + "\n"
    try:
        folder.mkdir(parents=True, exist_ok=True)
        if sys.platform != "win32":
            folder.chmod(0o700)
        temp = path.with_name("." + FILE_NAME + ".tmp")
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)  # private from the start
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            out.write(document)
        os.replace(temp, path)
        if sys.platform != "win32":
            path.chmod(0o600)
            if stat.S_IMODE(path.stat().st_mode) & 0o077:
                raise OSError("permissions could not be restricted")
    except OSError as error:
        path.unlink(missing_ok=True)
        raise SettingsError(
            f"The settings could not be saved privately ({error}); nothing was saved."
        ) from error
    return path


def forget() -> bool:
    path = settings_path()
    existed = path.exists()
    path.unlink(missing_ok=True)
    return existed


def load() -> ClientSettings:
    """Environment variables first, then the file (BR1.1). Raises SettingsError if neither."""
    server = os.environ.get("MODELHUB_SERVER")
    token = os.environ.get("MODELHUB_TOKEN")
    if not (server and token):
        try:
            saved = json.loads(settings_path().read_text(encoding="utf-8"))
            server = server or saved.get("server")
            token = token or saved.get("token")
        except (OSError, ValueError):
            pass
    if not server or not token:
        raise SettingsError("No server or token is set. Run: modelhub login")
    return ClientSettings(check_address(server), token.strip())
