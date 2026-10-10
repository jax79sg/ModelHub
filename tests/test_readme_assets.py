import json

from conftest import COMMIT, FakeHub

from modelhub import pull, readme_assets

PNG = b"\x89PNG\r\n\x1a\n" + b"p" * 200


def test_find_pictures_in_markdown_and_html():
    text = (
        "![logo](https://x.test/a.png)\n"
        "<img src='https://x.test/b.png' width=10>\n"
        '![t](https://x.test/c.png "a title")\n'
        "![local](images/d.png)\n"
        "![again](https://x.test/a.png)\n"
    )
    assert readme_assets.find_pictures(text) == [
        "https://x.test/a.png",
        "https://x.test/b.png",
        "https://x.test/c.png",
        "images/d.png",
    ]


def test_outside_pictures_are_stored_locally_and_the_readme_is_rewritten(tmp_path, picture_server):
    picture_server.routes["/a.png"] = (200, PNG, 0)
    text = (
        f'# T\n![logo]({picture_server.base}/a.png)\nand <img src="{picture_server.base}/a.png">\n'
    )
    new_text, pictures = readme_assets.process_readme(text, tmp_path / "assets")
    assert picture_server.base not in new_text
    assert new_text.count("assets/") == 2
    stored = next((tmp_path / "assets").iterdir())
    assert stored.read_bytes() == PNG
    assert pictures == [
        {
            "source": f"{picture_server.base}/a.png",
            "local": f"readme/assets/{stored.name}",
            "status": "fetched",
        }
    ]
    assert len(picture_server.hits) == 1  # the same address is fetched once


def test_repository_pictures_are_left_alone_and_not_listed(tmp_path):
    new_text, pictures = readme_assets.process_readme("![x](images/d.png)", tmp_path / "assets")
    assert new_text == "![x](images/d.png)"
    assert pictures == []


def test_a_failed_picture_keeps_its_reference_and_is_listed(tmp_path, picture_server):
    picture_server.routes["/ok.png"] = (200, PNG, 0)
    text = f"![a]({picture_server.base}/ok.png) ![b]({picture_server.base}/missing.png)"
    new_text, pictures = readme_assets.process_readme(text, tmp_path / "assets")
    assert f"{picture_server.base}/missing.png" in new_text
    assert f"{picture_server.base}/ok.png" not in new_text
    assert {p["status"] for p in pictures} == {"fetched", "failed"}
    assert next(p for p in pictures if p["status"] == "failed")["local"] is None


def test_only_http_and_https_addresses_are_fetched(tmp_path, picture_server):
    text = "![a](file:///etc/passwd) ![b](ftp://x.test/a.png) ![c](data:image/png;base64,AAAA)"
    new_text, pictures = readme_assets.process_readme(text, tmp_path / "assets")
    assert new_text == text
    assert {p["status"] for p in pictures} == {"skipped"}
    assert not (tmp_path / "assets").exists() or not any((tmp_path / "assets").iterdir())


def test_a_picture_over_the_size_limit_is_skipped(tmp_path, picture_server):
    picture_server.routes["/big.png"] = (200, b"x" * 5000, 0)
    text = f"![a]({picture_server.base}/big.png)"
    new_text, pictures = readme_assets.process_readme(text, tmp_path / "assets", max_bytes=1000)
    assert new_text == text
    assert pictures[0]["status"] == "skipped"
    assert "larger" in pictures[0]["reason"]
    assert not any((tmp_path / "assets").glob("*")) if (tmp_path / "assets").exists() else True


def test_a_stalled_request_is_stopped_after_the_time_limit(tmp_path, picture_server):
    picture_server.routes["/slow.png"] = (200, PNG, 1)
    text = f"![a]({picture_server.base}/slow.png)"
    new_text, pictures = readme_assets.process_readme(text, tmp_path / "assets", timeout=0.2)
    assert new_text == text
    assert pictures[0]["status"] == "failed"


def test_default_limits_match_the_requirements():
    assert readme_assets.MAX_PICTURE_BYTES == 7 * 1024 * 1024
    assert readme_assets.PICTURE_TIMEOUT == 30


def test_pull_stores_pictures_and_writes_the_second_readme(tmp_path, picture_server):
    picture_server.routes["/logo.png"] = (200, PNG, 0)
    hub = FakeHub()
    readme = f"# Model\n![logo]({picture_server.base}/logo.png)\n".encode()
    hub.add_model("org/tiny", {"README.md": readme, "m.safetensors": b"w" * 50})
    pull.pull_model(hub, "org/tiny", tmp_path, selection={"all"})
    root = tmp_path / "models" / "org" / "tiny" / "commits" / COMMIT
    assert (root / "files" / "README.md").read_bytes() == readme  # original kept unchanged
    local = (root / "readme" / "README.local.md").read_text()
    assert picture_server.base not in local
    summary = json.loads((root / "summary.json").read_text())
    assert summary["readme"]["local"] == "readme/README.local.md"
    assert summary["readme"]["pictures"][0]["status"] == "fetched"
    stored = root / summary["readme"]["pictures"][0]["local"]
    assert stored.read_bytes() == PNG


def test_pull_survives_a_failed_picture(tmp_path, picture_server):
    hub = FakeHub()
    hub.add_model("org/tiny", {"README.md": f"![x]({picture_server.base}/none.png)".encode()})
    result = pull.pull_model(hub, "org/tiny", tmp_path, selection={"all"})
    root = tmp_path / "models" / "org" / "tiny" / "commits" / COMMIT
    summary = json.loads((root / "summary.json").read_text())
    assert summary["readme"]["pictures"][0]["status"] == "failed"
    assert result.pictures_failed == 1
