"""Display helpers that mimic how huggingface.co formats numbers, sizes and times."""

from __future__ import annotations

from datetime import datetime, timezone

# pipeline_tag id -> (label, colour group). Colour groups map to CSS custom properties.
PIPELINES: dict[str, tuple[str, str]] = {
    "text-generation": ("Text Generation", "red"),
    "text-classification": ("Text Classification", "red"),
    "token-classification": ("Token Classification", "red"),
    "question-answering": ("Question Answering", "red"),
    "fill-mask": ("Fill-Mask", "red"),
    "summarization": ("Summarization", "red"),
    "translation": ("Translation", "red"),
    "text2text-generation": ("Text2Text Generation", "red"),
    "zero-shot-classification": ("Zero-Shot Classification", "red"),
    "sentence-similarity": ("Sentence Similarity", "red"),
    "feature-extraction": ("Feature Extraction", "gray"),
    "table-question-answering": ("Table Question Answering", "red"),
    "image-classification": ("Image Classification", "blue"),
    "object-detection": ("Object Detection", "blue"),
    "image-segmentation": ("Image Segmentation", "blue"),
    "image-to-text": ("Image-to-Text", "blue"),
    "image-text-to-text": ("Image-Text-to-Text", "orange"),
    "image-to-image": ("Image-to-Image", "blue"),
    "text-to-image": ("Text-to-Image", "blue"),
    "text-to-video": ("Text-to-Video", "blue"),
    "image-to-video": ("Image-to-Video", "blue"),
    "depth-estimation": ("Depth Estimation", "blue"),
    "zero-shot-image-classification": ("Zero-Shot Image Classification", "blue"),
    "any-to-any": ("Any-to-Any", "orange"),
    "automatic-speech-recognition": ("Automatic Speech Recognition", "green"),
    "text-to-speech": ("Text-to-Speech", "green"),
    "audio-classification": ("Audio Classification", "green"),
    "audio-to-audio": ("Audio-to-Audio", "green"),
    "reinforcement-learning": ("Reinforcement Learning", "purple"),
    "robotics": ("Robotics", "purple"),
    "tabular-classification": ("Tabular Classification", "gray"),
    "tabular-regression": ("Tabular Regression", "gray"),
    "time-series-forecasting": ("Time Series Forecasting", "gray"),
    "video-classification": ("Video Classification", "blue"),
}

LIBRARIES: dict[str, str] = {
    "transformers": "Transformers",
    "pytorch": "PyTorch",
    "tf": "TensorFlow",
    "tensorflow": "TensorFlow",
    "jax": "JAX",
    "flax": "Flax",
    "tflite": "LiteRT",
    "rust": "Rust",
    "onnx": "ONNX",
    "safetensors": "Safetensors",
    "gguf": "GGUF",
    "diffusers": "Diffusers",
    "sentence-transformers": "sentence-transformers",
    "openvino": "OpenVINO",
    "keras": "Keras",
    "peft": "PEFT",
    "timm": "timm",
    "mlx": "MLX",
    "spacy": "spaCy",
    "adapter-transformers": "Adapters",
    "coreml": "Core ML",
    "tensorboard": "TensorBoard",
}

LANGUAGES: dict[str, str] = {
    "en": "English",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "it": "Italian",
    "pt": "Portuguese",
    "nl": "Dutch",
    "ru": "Russian",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "ar": "Arabic",
    "hi": "Hindi",
    "tr": "Turkish",
    "pl": "Polish",
    "vi": "Vietnamese",
    "id": "Indonesian",
    "sv": "Swedish",
    "uk": "Ukrainian",
    "multilingual": "Multilingual",
}

# Parameter slider stops, as on the Hub: <1B, 6B, 12B, 32B, 128B, >500B.
PARAM_LABELS = ["< 1B", "6B", "12B", "32B", "128B", "> 500B"]
PARAM_LOWER = [0, 6e9, 12e9, 32e9, 128e9, 500e9]
PARAM_UPPER = [1e9, 6e9, 12e9, 32e9, 128e9, float("inf")]


def pipeline_label(tag: str | None) -> str:
    if not tag:
        return ""
    return PIPELINES.get(tag, (tag.replace("-", " ").title(), "gray"))[0]


def pipeline_color(tag: str | None) -> str:
    return PIPELINES.get(tag or "", ("", "gray"))[1]


def library_label(tag: str) -> str:
    return LIBRARIES.get(tag, tag)


def language_label(tag: str) -> str:
    return LANGUAGES.get(tag, tag)


def count(n: int | None) -> str:
    """4220 -> 4.22k, 15559744 -> 15.6M (three significant figures, like the Hub)."""
    if n is None:
        return "–"
    units = ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "k"))
    for i, (limit, suffix) in enumerate(units):
        if n >= limit:
            text = f"{n / limit:.3g}"
            if float(text) >= 1000 and i > 0:  # 999.7k rounds up to 1M
                return f"1{units[i - 1][1]}"
            return text + suffix
    return str(n)


def size(n: int | None) -> str:
    """Decimal units, like the Hub: 445 Bytes, 8.09 kB, 125 MB, 5.63 GB."""
    if n is None:
        return "–"
    if n < 1000:
        return f"{n} Bytes"
    v = float(n)
    for unit in ("kB", "MB", "GB", "TB"):
        v /= 1000
        if v < 1000 or unit == "TB":
            digits = 2 if v < 10 else (1 if v < 100 else 0)
            return f"{v:.{digits}f} {unit}"
    return f"{n} Bytes"


def params(n: int | None) -> str | None:
    """744371512 -> 0.7B, 17390336 -> 17.4M, 4433468 -> 4.43M."""
    if n is None:
        return None
    if n >= 1e8:  # the Hub switches to billions from 100M: 744M shows as 0.7B
        v = n / 1e9
        return f"{v:.0f}B" if v >= 10 else f"{v:.1f}B"
    if n >= 1e6:
        v = n / 1e6
        return f"{v:.1f}M" if v >= 10 else f"{v:.2f}M"
    if n >= 1e3:
        return f"{n / 1e3:.0f}K"
    return str(n)


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def time_ago(value: str | None, now: datetime | None = None) -> str:
    """date-fns style: 'about 2 hours ago', '5 days ago', 'over 2 years ago'."""
    dt = parse_time(value)
    if dt is None:
        return "unknown"
    seconds = max(0, int(((now or datetime.now(timezone.utc)) - dt).total_seconds()))
    minutes = round(seconds / 60)
    if minutes < 1:
        return "less than a minute ago"
    if minutes < 2:
        return "1 minute ago"
    if minutes < 45:
        return f"{minutes} minutes ago"
    if minutes < 90:
        return "about 1 hour ago"
    hours = round(minutes / 60)
    if hours < 24:
        return f"about {hours} hours ago"
    days = round(hours / 24)
    if days < 2:
        return "1 day ago"
    if days < 30:
        return f"{days} days ago"
    if days < 45:
        return "about 1 month ago"
    if days < 60:
        return "about 2 months ago"
    months = round(days / 30)
    if months < 12:
        return f"{months} months ago"
    years, rem = divmod(days, 365)
    if rem < 91:
        base = "about"
    elif rem < 274:
        base = "over"
    else:
        base, years = "almost", years + 1
    return f"{base} {years} year{'s' if years != 1 else ''} ago"


def date_long(value: str | None) -> str:
    dt = parse_time(value)
    return f"{dt.strftime('%b')} {dt.day}, {dt.year}" if dt else "unknown"


def datetime_iso(value: str | None) -> str:
    dt = parse_time(value)
    return dt.strftime("%Y-%m-%d %H:%M UTC") if dt else "unknown"
