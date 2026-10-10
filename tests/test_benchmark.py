"""The download-speed benchmark (NFR1.1): the parts that can be checked without the internet."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load():
    spec = importlib.util.spec_from_file_location(
        "benchmark", ROOT / "tools" / "benchmark_download.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_peak_rate_is_the_best_window_not_the_average():
    samples = [(0, 0), (1, 100), (2, 300), (3, 700), (10, 800)]
    assert (
        load().peak_window_rate(samples, window=2) == 300.0
    )  # bytes 100 to 700 over seconds 1 to 3


def test_a_run_shorter_than_the_window_uses_the_whole_run():
    assert load().peak_window_rate([(0, 0), (2, 500)], window=5) == 250.0


def test_no_samples_means_no_rate():
    assert load().peak_window_rate([], window=5) == 0.0
    assert load().peak_window_rate([(0, 0)], window=5) == 0.0


def test_the_ratio_compares_the_tool_with_the_connection():
    bench = load()
    assert bench.ratio(80.0, 100.0) == 0.8
    assert bench.ratio(50.0, 0.0) is None


def test_the_target_is_eighty_percent_of_the_connection():
    bench = load()
    assert bench.TARGET == 0.8
    assert bench.passed(0.8) is True and bench.passed(0.79) is False and bench.passed(None) is False


def test_the_saved_result_records_what_is_needed_to_compare_runs():
    bench = load()
    doc = bench.result_document(
        model="org/model",
        file="model.safetensors",
        file_bytes=1000,
        tool_rate=90.0,
        link_rate=100.0,
        seconds=12.5,
    )
    assert doc["model"] == "org/model" and doc["file"] == "model.safetensors"
    assert doc["ratio"] == 0.9 and doc["passed"] is True and doc["target"] == 0.8
    assert doc["date"].endswith("Z")
    assert {"system", "machine", "python"} <= set(doc["platform"])
    assert doc["tool_rate_bytes_per_s"] == 90.0 and doc["link_rate_bytes_per_s"] == 100.0
