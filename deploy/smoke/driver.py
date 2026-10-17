"""Plays a browser and an import computer against the running stack, through the proxy.

``import``  trusts a signing key on the portal, makes a token, runs ``modelhub import`` and
            checks the model is listed.
``check``   checks the model is still listed after an upgrade or a return, and that importing
            it again is skipped.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import httpx

PORTAL = os.environ.get("PORTAL", "https://modelhub.test:8443")
STATE = Path(os.environ.get("STATE", "/state"))
MODEL = "org/tiny"


def browser(who: str, admin: bool = False) -> httpx.Client:
    client = httpx.Client(follow_redirects=False, timeout=60)
    r = client.get(PORTAL + "/auth/login")
    hop = r.headers["location"] + f"&login_hint={who}" + ("&admin=1" if admin else "")
    for _ in range(6):
        r = client.get(hop)
        if r.status_code != 302:
            break
        hop = r.headers["location"]
        if hop.startswith("/"):
            hop = PORTAL + hop
    assert r.status_code == 200, f"sign-in ended with {r.status_code}"
    return client


def csrf(client: httpx.Client, path: str) -> str:
    html = client.get(PORTAL + path).text
    return re.search(r'name="_csrf" value="([^"]+)"', html).group(1)


def make_token(who: str) -> str:
    ada = browser(who)
    made = ada.post(
        PORTAL + "/account/tokens",
        data={"name": "smoke", "_csrf": csrf(ada, "/account/tokens")},
        headers={"Origin": PORTAL},
    )
    return re.search(r'id="new-token">(mhi_[^<]+)<', made.text).group(1)


def run_import(token: str, home: Path) -> str:
    env = {
        **os.environ,
        "MODELHUB_SERVER": PORTAL,
        "MODELHUB_TOKEN": token,
        "MODELHUB_HOME": str(home),
    }
    done = subprocess.run(
        [sys.executable, "-m", "modelhub", "import", str(STATE / "bundle")],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    print(done.stdout, done.stderr, flush=True)
    assert done.returncode == 0, f"import exited {done.returncode}"
    assert token not in done.stdout + done.stderr
    return done.stdout


def listed() -> None:
    ada = browser("ada")
    assert MODEL in ada.get(PORTAL + "/models").text, "the model is not in the portal list"
    page = ada.get(f"{PORTAL}/{MODEL}")
    assert page.status_code == 200 and "Tiny" in page.text, "the model page is wrong"


def first_import() -> None:
    from modelhub_testkit.bundles import make_bundle

    from modelhub import signing

    STATE.mkdir(parents=True, exist_ok=True)
    bundle = make_bundle(STATE / "make", model_id=MODEL)
    target = STATE / "bundle"
    target.mkdir(exist_ok=True)
    for path in bundle.directory.iterdir():
        (target / path.name).write_bytes(path.read_bytes())
    (STATE / "public.json").write_text(json.dumps(bundle.public_key))

    root = browser("root", admin=True)
    added = root.post(
        PORTAL + "/admin/keys",
        data={
            "name": "smoke key",
            "public_key": json.dumps(bundle.public_key),
            "fingerprint": bundle.public_key["fingerprint"],
            "_csrf": csrf(root, "/admin/keys"),
        },
        headers={"Origin": PORTAL},
    )
    assert added.status_code == 303, f"adding the key gave {added.status_code}"

    home = STATE / "computer"
    os.environ["MODELHUB_HOME"] = str(home)
    signing.trust_key(bundle.public_key, bundle.public_key["fingerprint"])
    out = run_import(make_token("ada"), home)
    assert "IMPORTED" in out, out
    listed()


def check() -> None:
    listed()
    home = STATE / "computer"
    out = run_import(make_token("ada"), home)
    assert "SKIPPED" in out, out


if __name__ == "__main__":
    {"import": first_import, "check": check}[sys.argv[1]]()
    print(f"driver {sys.argv[1]}: ok", flush=True)
