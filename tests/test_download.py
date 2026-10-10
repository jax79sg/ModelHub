import random

import pytest
from conftest import COMMIT, FakeHub

from modelhub import download, pull
from modelhub.hubclient import ModelNotFound, RateLimited, TransientHubError


def files_dir(tmp_path):
    return tmp_path / "models" / "org" / "tiny" / "commits" / COMMIT / "files"


def tree_entries(hub, repo="org/tiny"):
    return [e for e in hub.models[repo]["tree"] if e["type"] == "file"]


class Clock:
    """Records waits instead of sleeping."""

    def __init__(self):
        self.waits = []

    def sleep(self, seconds):
        self.waits.append(seconds)


def run_fetch(hub, tmp_path, clock, workers=8, policy=None, waiting=None, repo="org/tiny"):
    return download.fetch_files(
        hub,
        repo,
        COMMIT,
        tree_entries(hub, repo),
        tmp_path / "files",
        workers=workers,
        policy=policy or download.RetryPolicy(jitter=0),
        sleep=clock.sleep,
        on_wait=waiting,
    )


def test_transient_errors_are_retried_with_growing_waits(fake_hub, tmp_path):
    fake_hub.failures["config.json"] = [TransientHubError("x")] * 3
    clock = Clock()
    outcome = run_fetch(fake_hub, tmp_path, clock)
    assert outcome.failed == []
    assert clock.waits == [1, 2, 4]
    assert (tmp_path / "files" / "config.json").is_file()


def test_five_retries_then_success(fake_hub, tmp_path):
    fake_hub.failures["config.json"] = [TransientHubError("x")] * 5
    clock = Clock()
    outcome = run_fetch(fake_hub, tmp_path, clock)
    assert outcome.failed == []
    assert clock.waits == [1, 2, 4, 8, 16]


def test_after_the_last_retry_the_file_is_failed_and_the_others_still_finish(fake_hub, tmp_path):
    fake_hub.failures["config.json"] = [TransientHubError("down")] * 6
    clock = Clock()
    outcome = run_fetch(fake_hub, tmp_path, clock)
    assert [f["path"] for f in outcome.failed] == ["config.json"]
    assert "down" in outcome.failed[0]["reason"]
    assert (tmp_path / "files" / "model.safetensors").is_file()
    assert not (tmp_path / "files" / "config.json").exists()


def test_a_small_random_extra_wait_is_added(fake_hub, tmp_path):
    fake_hub.failures["config.json"] = [TransientHubError("x")] * 3
    clock = Clock()
    policy = download.RetryPolicy(jitter=0.5, rng=random.Random(7))
    run_fetch(fake_hub, tmp_path, clock, policy=policy)
    for wait, base in zip(clock.waits, [1, 2, 4], strict=True):
        assert base <= wait <= base * 1.5
    assert clock.waits != [1, 2, 4]


def test_rate_limit_wait_follows_the_servers_guidance_and_is_reported(fake_hub, tmp_path):
    fake_hub.failures["config.json"] = [RateLimited("slow down", retry_after=7)]
    clock, messages = Clock(), []
    run_fetch(fake_hub, tmp_path, clock, waiting=messages.append)
    assert clock.waits == [7]
    assert any("slow down" in m.lower() for m in messages)


def test_errors_that_will_not_get_better_are_not_retried(fake_hub, tmp_path):
    fake_hub.failures["config.json"] = [ModelNotFound("gone")]
    clock = Clock()
    outcome = run_fetch(fake_hub, tmp_path, clock)
    assert [f["path"] for f in outcome.failed] == ["config.json"]
    assert clock.waits == []
    assert fake_hub.downloads().count("config.json") == 1


def test_a_file_already_fetched_and_checked_is_not_fetched_again(fake_hub, tmp_path):
    clock = Clock()
    run_fetch(fake_hub, tmp_path, clock)
    before = len(fake_hub.downloads())
    outcome = run_fetch(fake_hub, tmp_path, clock)
    assert len(fake_hub.downloads()) == before
    assert outcome.fetched == []
    assert len(outcome.skipped) == len(tree_entries(fake_hub))


def test_a_damaged_earlier_copy_is_fetched_again(fake_hub, tmp_path):
    clock = Clock()
    run_fetch(fake_hub, tmp_path, clock)
    (tmp_path / "files" / "config.json").write_bytes(b"damaged")
    outcome = run_fetch(fake_hub, tmp_path, clock)
    assert outcome.fetched == ["config.json"]


def test_a_checksum_mismatch_fails_the_file_and_removes_it(fake_hub, tmp_path):
    fake_hub.corrupt.add("model.safetensors")
    clock = Clock()
    outcome = run_fetch(fake_hub, tmp_path, clock)
    assert [f["path"] for f in outcome.failed] == ["model.safetensors"]
    assert "checksum" in outcome.failed[0]["reason"].lower()
    assert not (tmp_path / "files" / "model.safetensors").exists()
    assert clock.waits == []


def many_files_hub(count=10):
    hub = FakeHub()
    hub.add_model("org/tiny", {f"f{i}.json": b"{}" for i in range(count)})
    hub.delay = 0.05
    return hub


def test_eight_files_download_at_the_same_time_by_default(tmp_path):
    hub = many_files_hub()
    run_fetch(hub, tmp_path, Clock())
    assert hub.max_active == 8


def test_the_number_of_simultaneous_downloads_can_be_changed(tmp_path):
    hub = many_files_hub()
    run_fetch(hub, tmp_path, Clock(), workers=2)
    assert hub.max_active == 2


def test_pull_with_a_failed_file_keeps_the_rest_and_writes_no_manifest(fake_hub, tmp_path):
    fake_hub.failures["config.json"] = [TransientHubError("down")] * 99
    with pytest.raises(pull.PullIncomplete) as error:
        pull.pull_model(fake_hub, "org/tiny", tmp_path, selection={"all"}, sleep=lambda s: None)
    assert [f["path"] for f in error.value.failed] == ["config.json"]
    root = tmp_path / "models" / "org" / "tiny" / "commits" / COMMIT
    assert (root / "files" / "model.safetensors").is_file()
    assert not (root / "manifest.json").exists()


def test_a_restarted_pull_fetches_only_what_is_missing(fake_hub, tmp_path):
    fake_hub.failures["config.json"] = [TransientHubError("down")] * 6
    with pytest.raises(pull.PullIncomplete):
        pull.pull_model(fake_hub, "org/tiny", tmp_path, selection={"all"}, sleep=lambda s: None)
    fake_hub.calls.clear()
    result = pull.pull_model(
        fake_hub, "org/tiny", tmp_path, selection={"all"}, sleep=lambda s: None
    )
    assert fake_hub.downloads() == ["config.json"]
    assert result.record_dir.joinpath("manifest.json").is_file()
