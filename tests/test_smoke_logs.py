"""The log search of the Docker smoke test (loop-back 2, platform NFR5.1).

`deploy/smoke/check_logs.py` reads the logs of every container and fails if any secret value is
in them. It names the secret's file, never its value.
"""

import base64
import os
import subprocess
import sys
from pathlib import Path

SMOKE = Path(__file__).resolve().parent.parent / "deploy" / "smoke"
SCRIPT = SMOKE / "check_logs.py"
BODY = [base64.b64encode(os.urandom(48)).decode() for _ in range(2)]  # random each run
PEM = "-----BEGIN " + "TEST KEY-----\n" + "\n".join(BODY) + "\n-----END " + "TEST KEY-----\n"


def search(tmp_path, secrets: dict[str, str], logs: str):
    folder = tmp_path / "secrets"
    folder.mkdir()
    for name, value in secrets.items():
        (folder / name).write_text(value, encoding="utf-8")
    log = tmp_path / "logs.txt"
    log.write_text(logs, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(folder), str(log)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_logs_without_any_secret_pass(tmp_path):
    done = search(
        tmp_path,
        {
            "token_hash_pepper": "pepper-1234567890abcdef\n",
            "artifactory_token": "tok-abcdefgh12345\n",
        },
        'catalog-1  | {"event":"request","status":200}\nproxy-1  | GET /models 200\n',
    )
    assert done.returncode == 0, done.stdout + done.stderr


def test_a_secret_in_the_logs_fails_and_only_its_file_is_named(tmp_path):
    secret = "tok-abcdefgh12345"
    done = search(
        tmp_path,
        {"artifactory_token": secret + "\n", "token_hash_pepper": "pepper-1234567890abcdef\n"},
        f"artifactory-service-1  | upload failed for {secret}\n",
    )
    assert done.returncode == 1
    out = done.stdout + done.stderr
    assert "artifactory_token" in out and secret not in out
    assert "token_hash_pepper" not in out


def test_one_line_of_a_multi_line_key_in_the_logs_is_found(tmp_path):
    done = search(
        tmp_path,
        {"tls_key": PEM},
        f"proxy-1  | {BODY[0]}\n",
    )
    assert done.returncode == 1 and "tls_key" in done.stdout + done.stderr


def test_the_begin_and_end_lines_of_a_key_do_not_count(tmp_path):
    done = search(tmp_path, {"tls_key": PEM}, "proxy-1  | loaded -----BEGIN TEST KEY----- ok\n")
    assert done.returncode == 0


def test_a_missing_secrets_folder_or_log_is_an_error_not_a_pass(tmp_path):
    done = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path / "nope"), str(tmp_path / "none.txt")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 2


def test_the_smoke_test_runs_the_search_after_the_rehearsal_and_before_it_passes():
    script = (SMOKE / "run.sh").read_text(encoding="utf-8")
    assert "check_logs.py" in script
    assert script.index("check_logs.py") > script.index('drive "$FROM" check')
    assert script.index("check_logs.py") < script.index("smoke test and rehearsal passed")
