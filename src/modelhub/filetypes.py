"""Group a model's files by type, with a plain-language explanation of each (FR2)."""

from __future__ import annotations

import posixpath
from dataclasses import dataclass, field


class UnknownFileType(ValueError):
    pass


@dataclass(frozen=True)
class FileType:
    key: str
    label: str
    explanation: str
    always: bool = False  # small files the web app cannot do without (FR2.5)


TYPES: dict[str, FileType] = {
    t.key: t
    for t in [
        FileType(
            "safetensors",
            "Weights (safetensors)",
            "The model's learned numbers in a plain format that cannot contain runnable code. "
            "This is the current standard.",
        ),
        FileType(
            "bin",
            "Weights (older PyTorch .bin, .pt, .pth, .ckpt)",
            "The older PyTorch format. It uses a method that can hide runnable code, "
            "which is why scanners check it.",
        ),
        FileType("h5", "Weights (TensorFlow/Keras)", "The same model for TensorFlow and Keras."),
        FileType("msgpack", "Weights (JAX/Flax)", "The same model for JAX and Flax."),
        FileType(
            "onnx",
            "Weights (ONNX)",
            "A format for running the model in many tools through ONNX Runtime, "
            "often in several variants.",
        ),
        FileType(
            "tflite",
            "Weights (TensorFlow Lite)",
            "Smaller versions meant for phones and small devices.",
        ),
        FileType("ot", "Weights (rust-bert)", "The model for the Rust library rust-bert."),
        FileType(
            "gguf",
            "Weights (GGUF)",
            "A compact format used by llama.cpp and Ollama, often in several sizes per model.",
        ),
        FileType(
            "settings",
            "Settings and word lists",
            "Small settings and word-list files needed to load the model, such as config and tokenizer files.",
            always=True,
        ),
        FileType(
            "readme",
            "README (model card)",
            "The model card shown on the model's page.",
            always=True,
        ),
        FileType(
            "licence", "Licence", "The licence file, when the repository has one.", always=True
        ),
        FileType(
            "image",
            "Pictures",
            "Pictures stored in the repository, usually shown in the README.",
            always=True,
        ),
        FileType("other", "Other files", "Anything that is none of the above."),
    ]
}

_BY_EXTENSION = {
    ".safetensors": "safetensors",
    ".bin": "bin",
    ".pt": "bin",
    ".pth": "bin",
    ".ckpt": "bin",
    ".pkl": "bin",
    ".h5": "h5",
    ".keras": "h5",
    ".msgpack": "msgpack",
    ".onnx": "onnx",
    ".onnx_data": "onnx",
    ".tflite": "tflite",
    ".ot": "ot",
    ".gguf": "gguf",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".gif": "image",
    ".svg": "image",
    ".webp": "image",
    ".json": "settings",
    ".txt": "settings",
    ".md": "settings",
    ".yaml": "settings",
    ".yml": "settings",
    ".toml": "settings",
    ".model": "settings",
}
_LICENCE_NAMES = ("license", "licence", "copying", "notice")


def classify(path: str) -> FileType:
    name = posixpath.basename(path).lower()
    if name.startswith("readme"):
        return TYPES["readme"]
    if name.startswith(_LICENCE_NAMES):
        return TYPES["licence"]
    if name.startswith("."):
        return TYPES["settings"]
    return TYPES[_BY_EXTENSION.get(posixpath.splitext(name)[1], "other")]


@dataclass
class TypeGroup:
    type: FileType
    count: int = 0
    size: int = 0
    paths: list[str] = field(default_factory=list)


def group_files(entries: list[dict]) -> list[TypeGroup]:
    groups: dict[str, TypeGroup] = {}
    for entry in entries:
        file_type = classify(entry["path"])
        group = groups.setdefault(file_type.key, TypeGroup(file_type))
        group.count += 1
        group.size += entry.get("size", 0)
        group.paths.append(entry["path"])
    return sorted(groups.values(), key=lambda g: (-g.size, g.type.key))


def total_size(groups: list[TypeGroup]) -> int:
    return sum(g.size for g in groups)


def _check(selected: set[str]) -> None:
    unknown = sorted(selected - set(TYPES) - {"all"})
    if unknown:
        valid = ", ".join(sorted(set(TYPES) | {"all"}))
        raise UnknownFileType(
            f"unknown file type {', '.join(map(repr, unknown))}; valid types: {valid}"
        )


def choose(entries: list[dict], selected: set[str]) -> list[dict]:
    """The files to fetch: the selected types, plus the always-fetched small files."""
    _check(selected)
    if "all" in selected:
        return list(entries)
    return [e for e in entries if classify(e["path"]).always or classify(e["path"]).key in selected]


def selected_weight_files(entries: list[dict], selected: set[str]) -> list[dict]:
    """Files matched by the selection itself, not by the always-fetched rule."""
    _check(selected)
    return [
        e
        for e in entries
        if not classify(e["path"]).always
        and ("all" in selected or classify(e["path"]).key in selected)
    ]
