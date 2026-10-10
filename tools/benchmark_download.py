"""Download-speed benchmark (NFR1.1): the tool must reach 80% of what the connection can do.

Run by hand on a connected machine:  python tools/benchmark_download.py org/model file.bin
The connection's best rate is measured with plain parallel range requests on the same file; the
tool's rate is measured by pulling that one file with `modelhub`. The link rate is the best 5 s window of steady parallel streams; the tool rate is the whole-transfer average,
because the fast-transfer route writes in bursts that make a short window look too fast.
"""

import argparse
import json
import platform
import sys
import tempfile
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

TARGET = 0.8
WINDOW = 5.0


def peak_window_rate(samples, window=WINDOW):
    """Best bytes-per-second over any span of `window` seconds in (time, total_bytes) samples."""
    if len(samples) < 2:
        return 0.0
    best = 0.0
    for i, (t0, b0) in enumerate(samples):
        later = [(t, b) for t, b in samples[i + 1 :] if t - t0 >= window]
        end = later[0] if later else samples[-1]
        if end[0] > t0:
            best = max(best, (end[1] - b0) / (end[0] - t0))
        if not later:
            break
    return best


def ratio(tool_rate, link_rate):
    return None if not link_rate else tool_rate / link_rate


def passed(value):
    return value is not None and value >= TARGET


def result_document(model, file, file_bytes, tool_rate, link_rate, seconds):
    value = ratio(tool_rate, link_rate)
    return {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model": model,
        "file": file,
        "file_bytes": file_bytes,
        "seconds": seconds,
        "tool_rate_bytes_per_s": tool_rate,
        "link_rate_bytes_per_s": link_rate,
        "ratio": value,
        "target": TARGET,
        "passed": passed(value),
        "platform": {
            "system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
    }


def measure_link(url, size, streams=8, limit=512 * 1024 * 1024):
    """Plain parallel range requests: roughly what the connection can carry."""
    total = min(size, limit)
    part = total // streams
    samples, count, lock, start = [(0.0, 0)], [0], threading.Lock(), time.monotonic()

    def fetch(n):
        lo = n * part
        req = urllib.request.Request(url, headers={"Range": f"bytes={lo}-{lo + part - 1}"})
        with urllib.request.urlopen(req) as resp:
            while chunk := resp.read(1 << 20):
                with lock:
                    count[0] += len(chunk)
                    samples.append((time.monotonic() - start, count[0]))

    with ThreadPoolExecutor(streams) as pool:
        list(pool.map(fetch, range(streams)))
    return peak_window_rate(samples)


def measure_tool(model, file):
    from modelhub.hubclient import HfHubClient
    from modelhub.pull import pull_model

    samples, start = [(0.0, 0)], time.monotonic()
    with tempfile.TemporaryDirectory() as work:
        stop = threading.Event()

        def watch():
            while not stop.wait(0.5):
                done = sum(p.stat().st_size for p in Path(work).rglob("*") if p.is_file())
                samples.append((time.monotonic() - start, done))

        watcher = threading.Thread(target=watch, daemon=True)
        watcher.start()
        pull_model(HfHubClient(), model, Path(work), selection={Path(file).suffix.lstrip(".")})
        stop.set()
        watcher.join()
        size = max(b for _, b in samples)
    seconds = time.monotonic() - start
    return size / seconds, size, seconds  # whole-transfer average: fast transfer writes in bursts


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("model")
    ap.add_argument("file")
    ap.add_argument("--out", type=Path, default=Path("benchmark-result.json"))
    args = ap.parse_args(argv)
    url = f"https://huggingface.co/{args.model}/resolve/main/{args.file}"
    head = urllib.request.urlopen(urllib.request.Request(url, method="HEAD"))
    size = int(head.headers["Content-Length"])
    link = measure_link(url, size)
    tool, got, seconds = measure_tool(args.model, args.file)
    doc = result_document(args.model, args.file, got or size, tool, link, seconds)
    args.out.write_text(json.dumps(doc, indent=2) + "\n")
    print(json.dumps(doc, indent=2))
    return 0 if doc["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
