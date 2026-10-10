import io
import threading

from modelhub import progress


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def make(is_tty, **kwargs):
    clock = FakeClock()
    out = io.StringIO()
    return progress.Reporter(out=out, is_tty=is_tty, clock=clock, **kwargs), clock, out


def run_for(reporter, clock, seconds, step=0.5, per_step=100):
    for _ in range(int(seconds / step)):
        clock.now += step
        reporter.advance(per_step)


def test_a_terminal_display_changes_at_least_every_two_seconds():
    reporter, clock, out = make(True)
    reporter.start("model.safetensors", total_bytes=10_000)
    run_for(reporter, clock, 10)
    updates = [u for u in out.getvalue().split("\r") if u.strip()]
    assert len(updates) >= 5  # ten seconds, at least one every two


def test_a_terminal_display_shows_item_bytes_rate_and_time_left():
    reporter, clock, out = make(True)
    reporter.start("download", total_bytes=1000)
    reporter.advance(0, item="model.safetensors")
    clock.now = 4.0
    reporter.advance(500)
    text = out.getvalue()
    assert "model.safetensors" in text
    assert "500 bytes of 1000 bytes" in text or "500 B of 1.0 KB" in text
    assert "50%" in text
    assert "125" in text  # about 125 bytes a second
    assert "4 s left" in text


def test_without_a_terminal_a_plain_line_is_written_at_least_every_thirty_seconds():
    reporter, clock, out = make(False)
    reporter.start("bundle", total_bytes=1_000_000)
    run_for(reporter, clock, 100, step=1.0, per_step=1000)
    lines = [line for line in out.getvalue().splitlines() if line.strip()]
    assert 3 <= len(lines) <= 4
    assert "\r" not in out.getvalue()
    assert all("bundle" in line for line in lines)


def test_a_short_step_shows_no_progress_at_all():
    reporter, clock, out = make(True)
    reporter.start("quick", total_bytes=100)
    clock.now = 1.0
    reporter.advance(100)
    reporter.finish()
    assert out.getvalue() == ""


def test_when_the_total_is_unknown_it_shows_bytes_and_rate_without_percent():
    reporter, clock, out = make(True)
    reporter.start("stream")
    clock.now = 4.0
    reporter.advance(400)
    assert "%" not in out.getvalue()
    assert "100" in out.getvalue()


def test_finish_ends_the_line_so_the_next_message_starts_clean():
    reporter, clock, out = make(True)
    reporter.start("x", total_bytes=10)
    clock.now = 5.0
    reporter.advance(5)
    reporter.finish()
    assert out.getvalue().endswith("\n")


def test_ticks_keep_the_display_alive_even_when_no_bytes_arrive():
    reporter, clock, out = make(True)
    reporter.start("waiting", total_bytes=10)
    for _ in range(10):
        clock.now += 1.0
        reporter.tick()
    assert len([u for u in out.getvalue().split("\r") if u.strip()]) >= 4


def test_the_display_never_contains_colour_codes_or_a_secret(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "hf_SuperSecretToken1234567890")
    reporter, clock, out = make(True)
    reporter.start("file hf_SuperSecretToken1234567890.bin", total_bytes=10)
    clock.now = 5.0
    reporter.advance(5)
    assert "\x1b" not in out.getvalue()
    assert "SuperSecret" not in out.getvalue()


def test_notices_such_as_rate_limit_waits_are_always_shown_on_their_own_line():
    reporter, _clock, out = make(True)
    reporter.start("x", total_bytes=10)
    reporter.message("Hugging Face asked us to slow down; waiting 7 s")
    assert "slow down" in out.getvalue()
    assert out.getvalue().rstrip().endswith("7 s")


def test_many_threads_can_report_progress_at_once():
    reporter, _clock, _out = make(False)
    reporter.start("t", total_bytes=80_000)
    threads = [
        threading.Thread(target=lambda: [reporter.advance(10) for _ in range(1000)])
        for _ in range(8)
    ]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert reporter.bytes_done == 80_000


def test_the_null_reporter_accepts_every_call_and_shows_nothing():
    reporter = progress.NullReporter()
    reporter.start("x", total_bytes=1)
    reporter.advance(1, item="y")
    reporter.tick()
    reporter.message("m")
    reporter.finish()


class Spy(progress.NullReporter):
    """Counts what the commands report, to prove the display is wired in."""

    def __init__(self):
        self.labels, self.total, self.done, self.items_done, self.finished = [], None, 0, 0, False

    def start(self, label, total_bytes=None, total_items=None):
        self.labels.append(label)
        self.total = total_bytes

    def advance(self, nbytes=0, item=None, item_done=False):
        self.done += nbytes
        self.items_done += 1 if item_done else 0

    def finish(self):
        self.finished = True


def test_bundling_reports_every_byte_it_writes(pulled, key_id, tmp_path):
    from modelhub import bundle

    spy = Spy()
    result = bundle.bundle_record(pulled, tmp_path / "o", key_id, piece_size=4096, progress=spy)
    assert spy.total == result.stream_size and spy.done == result.stream_size and spy.finished


def test_unpacking_reports_every_byte_it_reads(bundle_dir, tmp_path):
    import json

    from modelhub import unpack

    spy = Spy()
    unpack.unpack_bundle([bundle_dir], tmp_path / "store", progress=spy)
    stream = json.loads(next(bundle_dir.glob("*.bundle.json")).read_text())["stream"]["size"]
    assert spy.total == stream and spy.done >= stream and spy.finished


def test_checking_pieces_reports_every_byte_it_hashes(bundle_dir):
    from modelhub import verify

    spy = Spy()
    verify.verify_bundle([bundle_dir], progress=spy)
    total = sum(p.stat().st_size for p in bundle_dir.glob("*.part-*"))
    assert spy.total == total and spy.done == total and spy.finished


def test_downloads_report_each_file_and_its_size(fake_hub, tmp_path):
    from modelhub import pull

    spy = Spy()
    pull.pull_model(fake_hub, "org/tiny", tmp_path, selection={"all"}, progress=spy)
    sizes = sum(len(d) for d in fake_hub.models["org/tiny"]["files"].values())
    assert spy.done == sizes and spy.items_done == len(fake_hub.models["org/tiny"]["files"])
    assert spy.finished


def test_human_sizes_and_durations_read_easily():
    assert progress.human_bytes(999) == "999 B"
    assert progress.human_bytes(1_500_000) == "1.5 MB"
    assert progress.human_duration(45) == "45 s"
    assert progress.human_duration(3725) == "1 h 2 min"
