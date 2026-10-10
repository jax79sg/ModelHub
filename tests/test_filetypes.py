import pytest

from modelhub import filetypes


@pytest.mark.parametrize(
    ("path", "key"),
    [
        ("model.safetensors", "safetensors"),
        ("model-00001-of-00002.safetensors", "safetensors"),
        ("pytorch_model.bin", "bin"),
        ("tf_model.h5", "h5"),
        ("flax_model.msgpack", "msgpack"),
        ("onnx/decoder_model.onnx", "onnx"),
        ("64-fp16.tflite", "tflite"),
        ("rust_model.ot", "ot"),
        ("model-q4_k_m.gguf", "gguf"),
        ("config.json", "settings"),
        ("vocab.txt", "settings"),
        ("README.md", "readme"),
        ("LICENSE", "licence"),
        ("license.txt", "licence"),
        ("assets/logo.png", "image"),
        ("weird.xyz", "other"),
    ],
)
def test_classify_puts_each_file_in_its_type(path, key):
    assert filetypes.classify(path).key == key


def test_every_type_has_a_plain_language_explanation():
    for file_type in filetypes.TYPES.values():
        assert len(file_type.explanation) > 20, file_type.key
        assert file_type.label


def entries(*items):
    return [{"path": p, "size": s} for p, s in items]


def test_group_files_counts_and_sums_sizes_per_type():
    groups = filetypes.group_files(
        entries(
            ("a.safetensors", 100),
            ("b.safetensors", 50),
            ("pytorch_model.bin", 80),
            ("config.json", 1),
        )
    )
    by_key = {g.type.key: g for g in groups}
    assert by_key["safetensors"].count == 2
    assert by_key["safetensors"].size == 150
    assert by_key["bin"].size == 80
    assert filetypes.total_size(groups) == 231
    assert groups[0].type.key == "safetensors"  # biggest first


def test_choose_adds_the_always_fetched_types_to_the_selection():
    files = entries(
        ("m.safetensors", 10), ("pytorch_model.bin", 10), ("config.json", 1), ("README.md", 1)
    )
    chosen = filetypes.choose(files, {"safetensors"})
    assert {f["path"] for f in chosen} == {"m.safetensors", "config.json", "README.md"}


def test_choose_all_returns_every_file():
    files = entries(("m.safetensors", 10), ("pytorch_model.bin", 10), ("weird.xyz", 1))
    assert len(filetypes.choose(files, {"all"})) == 3


def test_choose_several_types():
    files = entries(
        ("m.safetensors", 10), ("pytorch_model.bin", 10), ("m.gguf", 10), ("config.json", 1)
    )
    chosen = filetypes.choose(files, {"safetensors", "gguf"})
    assert {f["path"] for f in chosen} == {"m.safetensors", "m.gguf", "config.json"}


def test_choose_rejects_an_unknown_type_and_lists_the_valid_ones():
    with pytest.raises(filetypes.UnknownFileType) as error:
        filetypes.choose(entries(("a.bin", 1)), {"safetensorz"})
    assert "safetensors" in str(error.value)


def test_matched_nothing_ignores_the_always_fetched_files():
    files = entries(("m.safetensors", 10), ("config.json", 1))
    assert filetypes.selected_weight_files(files, {"gguf"}) == []
    assert len(filetypes.selected_weight_files(files, {"safetensors"})) == 1
