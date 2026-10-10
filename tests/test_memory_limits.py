"""Every step reads and writes in blocks, so memory stays small however large the file is
(NFR1.3, NFR1.4). Peak memory is measured in a separate process."""

import subprocess
import sys
import textwrap

import pytest

LIMIT_MB = 150  # far below the 8 GB ceiling: a streaming tool stays close to its own size


FOOTER = """
usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
# macOS reports bytes, Linux kilobytes
print(usage / (1024 * 1024) if sys.platform == "darwin" else usage / 1024)
"""


def peak_mb(code: str) -> float:
    program = "import resource, sys\n" + textwrap.dedent(code) + FOOTER
    result = subprocess.run(
        [sys.executable, "-c", program], capture_output=True, text=True, check=True
    )
    return float(result.stdout.strip().splitlines()[-1])


@pytest.mark.skipif(sys.platform == "win32", reason="the resource module is not on Windows")
def test_checking_a_one_gigabyte_file_stays_within_a_small_memory_footprint(tmp_path):
    big = tmp_path / "big.bin"
    with open(big, "wb") as handle:
        handle.truncate(1_000_000_000)  # a sparse file: no disk used
    mb = peak_mb(
        f"""
        from modelhub import fsutil
        fsutil.sha256_file({str(big)!r})
        """
    )
    assert mb < LIMIT_MB, f"peak memory was {mb:.0f} MB"


@pytest.mark.skipif(sys.platform == "win32", reason="the resource module is not on Windows")
def test_bundling_and_rebuilding_a_large_file_stays_within_a_small_memory_footprint(tmp_path):
    mb = peak_mb(
        f"""
        import json, pathlib
        from modelhub import bundle, record, signing, unpack
        import os
        os.environ["MODELHUB_HOME"] = {str(tmp_path / "home")!r}
        work = pathlib.Path({str(tmp_path / "work")!r})
        paths = record.RecordPaths(work, "org/big", "c" * 40)
        paths.files.mkdir(parents=True)
        with open(paths.files / "big.bin", "wb") as handle:
            handle.truncate(256_000_000)
        manifest = record.new_manifest(
            "org/big", "c" * 40, "main", record.build_file_entries(paths.files, {{}}),
            "2026-01-01T00:00:00Z",
        )
        record.write_manifest(paths, manifest)
        doc = signing.create_key("t")
        out = pathlib.Path({str(tmp_path / "out")!r})
        bundle.bundle_record(paths.root, out, doc["key_id"], piece_size=64_000_000)
        signing.trust_key(doc, doc["fingerprint"])
        unpack.unpack_bundle([out], pathlib.Path({str(tmp_path / "store")!r}))
        """
    )
    assert mb < LIMIT_MB, f"peak memory was {mb:.0f} MB"
