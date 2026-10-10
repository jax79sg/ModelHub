from modelhub import summary

CAPTURED = "2026-02-03T04:05:06Z"


def info(**over):
    base = {
        "id": "org/name",
        "sha": "c" * 40,
        "downloads": 10,
        "likes": 2,
        "tags": ["a", "b"],
        "pipeline_tag": "text-generation",
        "library_name": "transformers",
        "createdAt": "2025-01-01T00:00:00.000Z",
        "lastModified": "2026-01-01T00:00:00.000Z",
        "usedStorage": 4096,
        "cardData": {"license": "apache-2.0", "language": ["en"], "tags": ["x"]},
        "safetensors": {"parameters": {"F32": 7}, "total": 7},
    }
    base.update(over)
    return base


def manifest(*paths):
    files = [
        {
            "path": p,
            "size": 3,
            "sha256": "d" * 64,
            "hub_sha256": None,
            "hub_oid": None,
            "scan": None,
        }
        for p in paths
    ]
    return {"model_id": "org/name", "commit": "c" * 40, "captured_at": CAPTURED, "files": files}


def build(info_=None, paths=("README.md", "model.safetensors"), **kwargs):
    return summary.build_summary(info_ or info(), manifest(*paths), CAPTURED, **kwargs)


def test_card_fields_come_from_the_hub_response():
    card = build()["card"]
    assert card == {
        "license": "apache-2.0",
        "language": ["en"],
        "tags": ["a", "b"],
        "pipeline_tag": "text-generation",
        "library_name": "transformers",
    }


def test_stats_are_a_snapshot_with_the_capture_time():
    result = build()
    assert result["captured_at"] == CAPTURED
    assert result["stats"]["downloads"] == 10
    assert result["stats"]["likes"] == 2
    assert result["stats"]["used_storage_bytes"] == 4096
    assert result["stats"]["parameter_counts"] == {"parameters": {"F32": 7}, "total": 7}
    assert result["created_at"] == "2025-01-01T00:00:00.000Z"
    assert result["last_modified"] == "2026-01-01T00:00:00.000Z"


def test_unknown_values_are_null_never_zero():
    result = build(info(downloads=None, likes=None, pipeline_tag=None, cardData=None))
    thin = {k: v for k, v in info().items() if k not in ("downloads", "likes", "usedStorage")}
    absent = build(thin)
    for stats in (result["stats"], absent["stats"]):
        assert stats["downloads"] is None
        assert stats["likes"] is None
    assert absent["stats"]["used_storage_bytes"] is None
    assert result["card"]["pipeline_tag"] is None
    assert result["card"]["license"] is None


def test_licence_file_is_named_when_the_repository_has_one():
    result = build(paths=("README.md", "LICENSE", "model.safetensors"))
    assert result["license"] == {
        "name": "apache-2.0",
        "file": "files/LICENSE",
        "text_available": True,
    }


def test_licence_text_not_available_is_recorded_when_only_a_name_exists():
    result = build(paths=("README.md", "model.safetensors"))
    assert result["license"] == {"name": "apache-2.0", "file": None, "text_available": False}


def test_no_licence_at_all():
    result = build(info(cardData={}), paths=("README.md",))
    assert result["license"] == {"name": None, "file": None, "text_available": False}


def test_files_carry_type_and_scan_results_from_the_manifest():
    m = manifest("model.safetensors")
    m["files"][0]["scan"] = {"status": "safe"}
    result = summary.build_summary(info(), m, CAPTURED)
    assert result["files"][0]["type"] == "safetensors"
    assert result["files"][0]["scan"] == {"status": "safe"}
    assert result["size_bytes"] == 3


def test_readme_and_history_pointers():
    result = build(readme_local="readme/README.local.md")
    assert result["readme"]["original"] == "files/README.md"
    assert result["readme"]["local"] == "readme/README.local.md"
    assert result["history"] == {"commits_file": "raw/commits.json", "refs_file": "raw/refs.json"}


def test_readme_original_is_null_when_there_is_no_readme():
    assert build(paths=("model.safetensors",))["readme"]["original"] is None
