"""Run the stand-in on its own (for whole-stack checks): ``python -m modelhub_stand_in``."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone

from .register import checklist_markdown
from .server import StandIn


class JsonLines(logging.Formatter):
    """The shared log shape (contract C7): ts, level, service, event, message, plus extras."""

    def format(self, record: logging.LogRecord) -> str:
        line = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname.lower(),
            "service": "stand-in",
            "event": getattr(record, "event", "log"),
            "message": record.getMessage(),
        }
        if hasattr(record, "status"):
            line["status"] = record.status
        return json.dumps(line)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="modelhub_stand_in", description=__doc__)
    parser.add_argument("--token", help="the one bearer token to accept")
    parser.add_argument("--repo-key", default="models-hf")
    parser.add_argument("--layout", choices=["flat", "nested"], default="flat")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="address to listen on; only a smoke-test container uses anything but 127.0.0.1",
    )
    parser.add_argument("--public-host", help="the name other containers use to reach it")
    parser.add_argument("--keep-limit-bytes", type=int, default=1024 * 1024)
    parser.add_argument("--checklist", action="store_true", help="print the checklist and exit")
    args = parser.parse_args(argv)
    if args.checklist:
        sys.stdout.write(checklist_markdown())
        return 0
    if not args.token:
        parser.error("--token is required")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLines())
    logger = logging.getLogger("modelhub.stand_in")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    with StandIn(
        token=args.token,
        repo_key=args.repo_key,
        layout=args.layout,
        port=args.port,
        host=args.host,
        allow_any_host=args.host != "127.0.0.1",
        public_host=args.public_host,
        keep_limit_bytes=args.keep_limit_bytes,
    ) as stand_in:
        print(f"stand-in listening on {stand_in.url} (endpoint {stand_in.hf_endpoint})", flush=True)
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
