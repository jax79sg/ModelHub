"""The portal in Google Chrome (portal NFR10.1, narrowed by the person to Chrome).

Playwright drives the installed Chrome through the real portal on real local ports (the
whole-stack harness): sign-in through the sign-in stand-in, the models list, a model page, the
token page and the theme toggle, with no error in the browser console. Only the current Chrome
is covered; previous versions, Edge and Firefox are not, by the person's choice. The test skips
with a clear message where Playwright or Chrome is not installed.
"""

import json
import re

import pytest
from modelhub_testkit.bundles import make_bundle
from test_whole_stack import _no_xet, browser_sign_in, stack  # noqa: F401 - fixtures

from modelhub import cli, signing

playwright_api = pytest.importorskip("playwright.sync_api", reason="needs: pip install playwright")


@pytest.fixture
def chrome():
    with playwright_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome", headless=True)
        except playwright_api.Error as exc:
            pytest.skip(f"Google Chrome is not installed: {str(exc).splitlines()[0]}")
        try:
            yield browser
        finally:
            browser.close()


@pytest.fixture
def imported(stack, tmp_path, monkeypatch):  # noqa: F811
    """One model imported through the real command, so the pages have something to show."""
    from typer.testing import CliRunner

    portal = stack["portal"].url
    bundle = make_bundle(tmp_path / "b")
    root = browser_sign_in(portal, who="root", admin=True)
    csrf = re.search(r'name="_csrf" value="([^"]+)"', root.get(portal + "/admin/keys").text)[1]
    root.post(
        portal + "/admin/keys",
        data={
            "name": "release key",
            "public_key": json.dumps(bundle.public_key),
            "fingerprint": bundle.public_key["fingerprint"],
            "_csrf": csrf,
        },
        headers={"Origin": portal},
    )
    ada = browser_sign_in(portal)
    page = ada.get(portal + "/account/tokens")
    csrf = re.search(r'name="_csrf" value="([^"]+)"', page.text)[1]
    made = ada.post(
        portal + "/account/tokens",
        data={"name": "laptop", "_csrf": csrf},
        headers={"Origin": portal},
    )
    token = re.search(r'id="new-token">(mhi_[^<]+)<', made.text)[1]
    monkeypatch.setenv("MODELHUB_HOME", str(tmp_path / "import-computer"))
    (tmp_path / "cwd").mkdir()
    monkeypatch.chdir(tmp_path / "cwd")
    signing.trust_key(bundle.public_key, bundle.public_key["fingerprint"])
    result = CliRunner().invoke(
        cli.app,
        ["import", str(bundle.directory)],
        env={"MODELHUB_SERVER": stack["service"].url, "MODELHUB_TOKEN": token},
    )
    assert result.exit_code == 0, result.output
    return bundle


def test_the_portal_works_in_chrome(chrome, stack, imported):  # noqa: F811
    portal = stack["portal"].url
    page = chrome.new_page()
    problems: list[str] = []
    page.on("console", lambda m: problems.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: problems.append(str(e)))
    page.on("requestfailed", lambda r: problems.append(f"request failed: {r.url}"))

    # sign in (the stand-in signs the browser in at once) and land on the list
    page.goto(portal + "/models")
    assert page.url.startswith(portal + "/models")
    assert "ModelHub" in page.title()
    page.wait_for_selector(".model-id")
    assert "org/tiny" in page.inner_text(".model-id")

    # the search box filters; the model page shows its files and the download command
    page.fill("input[name=search]", "tiny")
    page.keyboard.press("Enter")
    page.wait_for_selector(".model-id")
    page.click("text=org/tiny")
    page.wait_for_url(re.compile(r".*/org/tiny$"))
    assert "model.safetensors" in page.content()
    assert "jf hf download org/tiny" in page.content()

    # the token page makes a token and shows it once
    page.goto(portal + "/account/tokens")
    page.fill("#name", "from chrome")
    page.click("button:has-text('Make token')")
    page.wait_for_selector("#new-token")
    assert page.inner_text("#new-token").startswith("mhi_")

    # the theme toggle changes the theme and the choice is kept
    page.goto(portal + "/models")
    before = page.evaluate("document.documentElement.getAttribute('data-theme')")
    page.click("[data-theme-toggle]")
    after = page.evaluate("document.documentElement.getAttribute('data-theme')")
    assert after in ("light", "dark") and after != before
    page.reload()
    assert page.evaluate("document.documentElement.getAttribute('data-theme')") == after

    # nothing was blocked and nothing went wrong in the browser
    assert problems == []
    assert chrome.version  # a real browser answered
