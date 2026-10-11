"""``python -m hubsite --store ./store`` (or the ``hubsite`` command)."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(prog="hubsite", description="Browse a modelhub model store like huggingface.co/models.")
    parser.add_argument(
        "--store", default=os.environ.get("HUBSITE_STORE", "store"), help="model store made by `modelhub unpack` (default: ./store)"
    )
    parser.add_argument("--host", default="127.0.0.1", help="address to listen on (default: 127.0.0.1, this computer only)")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    import uvicorn

    from .app import create_app

    store = Path(args.store).expanduser()
    if not (store / "models").is_dir():
        parser.error(f"{store} has no models/ folder; point --store at a folder made by `modelhub unpack`")
    uvicorn.run(create_app(store), host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
