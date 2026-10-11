import pytest
from conftest import COMMIT, make_model

from hubsite import fmt
from hubsite.markdown import render


def ids(resp):
    import re

    return re.findall(r'class="model-id-text">([^<]+)<span class="slash">/</span>([^<]+)</span>', resp.text)


# ------------------------------------------------------------------ listing
def test_listing_default_sort_is_downloads(client):
    r = client.get("/models")
    assert r.status_code == 200
    order = ids(r)
    assert order[0] == ("acme", "alpha")  # 1000 downloads
    assert order[-1] == ("zed", "gamma")  # unknown downloads sort last, not crash


def test_listing_sort_likes_and_name(client):
    assert ids(client.get("/models?sort=likes"))[0] == ("acme", "beta")
    assert ids(client.get("/models?sort=name"))[0] == ("acme", "alpha")
    assert client.get("/models?sort=bogus").status_code == 200  # falls back, no 500


def test_filters(client):
    assert ids(client.get("/models?pipeline_tag=fill-mask")) == [("acme", "beta")]
    assert ids(client.get("/models?license=mit")) == [("acme", "alpha")]
    assert ids(client.get("/models?language=en")) == [("acme", "beta")]
    assert ids(client.get("/models?search=gam")) == [("zed", "gamma")]


def test_parameter_filter_excludes_unknown_counts(client):
    assert ids(client.get("/models?pmax=0")) == [("acme", "alpha")]  # < 1B; gamma has no count
    assert ids(client.get("/models?pmin=2&pmax=3")) == [("acme", "beta")]  # 20B sits between the 12B and 32B stops
    assert ids(client.get("/models?pmin=3&pmax=4")) == []  # 32B..128B excludes it


def test_bad_query_values_do_not_crash(client):
    assert client.get("/models?p=-5&pmin=99&pmax=-3").status_code == 200
    assert client.get("/models?p=999").status_code == 200


def test_pagination_30_per_page(tmp_path):
    from fastapi.testclient import TestClient

    from hubsite.app import create_app

    s = tmp_path / "s"
    for i in range(35):
        make_model(s, f"org/m{i:02d}", downloads=i)
    c = TestClient(create_app(s), headers={"accept": "text/html"})
    assert len(ids(c.get("/models"))) == 30
    assert len(ids(c.get("/models?p=1"))) == 5


def test_empty_store_shows_instructions(tmp_path):
    from fastapi.testclient import TestClient

    from hubsite.app import create_app

    (tmp_path / "models").mkdir()
    r = TestClient(create_app(tmp_path), headers={"accept": "text/html"}).get("/models")
    assert r.status_code == 200 and "modelhub unpack" in r.text


# --------------------------------------------------------------- model pages
def test_model_card_renders_readme_and_sidebar(client):
    r = client.get("/acme/alpha")
    assert r.status_code == 200
    assert "<strong>world</strong>" in r.text
    assert "5M params" in r.text or "5.00M params" in r.text
    assert "x/y" in r.text  # dataset from tags
    assert "arXiv:1234.5678" in r.text


def test_model_without_readme_or_metadata(client):
    r = client.get("/zed/gamma")
    assert r.status_code == 200 and "No model card" in r.text


def test_unknown_model_and_revision_are_404(client):
    assert client.get("/acme/nope").status_code == 404
    assert client.get("/acme/alpha?rev=nonsense").status_code == 404
    assert client.get("/acme/alpha/tree/nonsense").status_code == 404


def test_revision_by_commit_prefix(client):
    assert client.get(f"/acme/alpha?rev={COMMIT[:7]}").status_code == 200


def test_tree_lists_files_dirs_and_hides_cache(client):
    r = client.get("/acme/alpha/tree/main")
    assert "config.json" in r.text and "sub" in r.text
    assert ".modelhub-dl" not in r.text
    assert "not in store" in r.text  # missing.safetensors was listed by the Hub only
    assert client.get("/acme/alpha/tree/main/sub").status_code == 200
    assert client.get("/acme/alpha/tree/main/nodir").status_code == 404
    assert client.get("/acme/alpha/tree/main/.modelhub-dl").status_code == 404


def test_commits_page(client):
    r = client.get("/acme/alpha/commits/main")
    assert "Second" in r.text and "First" in r.text and "alice" in r.text


# ------------------------------------------------------------------- files
def test_blob_text_binary_and_missing(client):
    assert '"a": 1' in client.get("/acme/alpha/blob/main/config.json").text.replace("&#34;", '"')
    assert "binary file" in client.get("/acme/alpha/blob/main/weights.bin").text
    assert "not downloaded" in client.get("/acme/alpha/blob/main/missing.safetensors").text


def test_download_is_attachment_octet_stream(client):
    r = client.get("/acme/alpha/resolve/main/config.json")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/octet-stream"
    assert "attachment" in r.headers["content-disposition"]
    assert r.headers["x-content-type-options"] == "nosniff"


def test_traversal_and_hidden_paths_refused(client, store):
    (store.parent / "secret.txt").write_text("top secret")
    for url in (
        "/acme/alpha/resolve/main/../../../../../secret.txt",
        "/acme/alpha/resolve/main/..%2f..%2f..%2f..%2f..%2fsecret.txt",
        "/acme/alpha/raw/main/%2e%2e/%2e%2e/secret.txt",
        "/acme/alpha/resolve/main/.modelhub-dl/.cache/x.lock",
        "/acme/alpha/readme-asset/" + COMMIT + "/../../../../config.json",
        "/acme/alpha/readme-asset/" + COMMIT + "/..%2f..%2ffiles%2fconfig.json",
        "/..%2f..%2fetc/passwd",
        "/acme%2f..%2f..%2fx/y",
    ):
        r = client.get(url)
        assert r.status_code in (404, 400), url
        assert "top secret" not in r.text


def test_symlink_escaping_files_dir_is_refused(client, store):
    outside = store.parent / "outside.txt"
    outside.write_text("outside")
    link = store / "models/acme/alpha/commits" / COMMIT / "files" / "config.json"
    link.unlink()
    try:
        link.symlink_to(outside)
    except OSError:  # Windows without the symlink right
        pytest.skip("cannot create symlinks here")
    assert client.get("/acme/alpha/resolve/main/config.json").status_code == 404


def test_security_headers(client):
    h = client.get("/models").headers
    assert "script-src 'self'" in h["content-security-policy"]
    assert h["referrer-policy"] == "no-referrer"


def test_api(client):
    data = client.get("/api/models").json()
    assert [m["id"] for m in data][0] == "acme/alpha"
    assert client.get("/api/models/acme/alpha").json()["model_id"] == "acme/alpha"
    assert client.get("/api/models/acme/nope").status_code == 404


def test_new_commit_in_store_is_picked_up_without_restart(client, store):
    assert len(ids(client.get("/models"))) == 3
    make_model(store, "new/model")
    assert ("new", "model") in ids(client.get("/models"))


# --------------------------------------------------------------- markdown
def test_markdown_sanitised():
    html = render(
        "<script>alert(1)</script><img src=x onerror=alert(1)>[js](javascript:alert(1))\n\n"
        '![remote](https://evil.example/p.png)\n\n![local](assets/p.png)\n\n<a href="data:text/html,x">d</a>'
        '<style>body{display:none}</style><iframe src="https://e"></iframe>',
        "o/m",
        COMMIT,
        "main",
    ).html
    assert "<script" not in html and "onerror" not in html and "javascript:" not in html.replace("[js](javascript:alert(1))", "")
    assert "<style" not in html and "<iframe" not in html and "data:text" not in html
    assert "evil.example" not in html  # remote pictures never load
    assert "/o/m/readme-asset/" + COMMIT + "/assets/p.png" in html


def test_markdown_front_matter_stripped_and_toc():
    r = render("---\nlicense: mit\n---\n# A\n## B\n", "o/m", COMMIT, "main")
    assert "license: mit" not in r.html
    assert [(lvl, title) for lvl, _, title in r.toc] == [(1, "A"), (2, "B")]


def test_markdown_relative_links_point_at_blob():
    assert 'href="/o/m/blob/main/LICENSE"' in render("[l](LICENSE)", "o/m", COMMIT, "main").html
    assert "../" not in render("[l](../../etc/passwd)", "o/m", COMMIT, "main").html


# --------------------------------------------------------------- formatting
def test_fmt():
    assert fmt.count(4220) == "4.22k" and fmt.count(15559744) == "15.6M" and fmt.count(504) == "504" and fmt.count(None) == "–"
    assert fmt.size(445) == "445 Bytes" and fmt.size(8090) == "8.09 kB" and fmt.size(5_630_000_000) == "5.63 GB"
    assert fmt.params(744_371_512) == "0.7B" and fmt.params(17_390_336) == "17.4M" and fmt.params(None) is None
    assert fmt.time_ago("not a date") == "unknown"
