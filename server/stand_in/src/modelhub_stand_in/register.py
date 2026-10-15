"""The assumption register and the checklist for a real Artifactory (rule BR1.13, FR7.2, FR7.3)."""

from __future__ import annotations

import json
from importlib import resources


def load() -> list[dict]:
    text = resources.files("modelhub_stand_in").joinpath("assumptions.json").read_text("utf-8")
    return json.loads(text)


def checklist() -> list[dict]:
    """One line per behaviour that must be confirmed on a real Artifactory."""
    return [
        {
            "assumption": a["id"],
            "what_to_check": a["check"],
            "expected": a["behaviour"],
            "basis": a["basis"],
            "confirmed": "open",
        }
        for a in load()
        if a["confirm_on_real"]
    ]


def checklist_markdown() -> str:
    lines = [
        "# Checklist for a real Artifactory",
        "",
        (
            "Each line is something the stand-in assumes. Confirm it on a real instance and note "
            "any difference."
        ),
        "",
        "| Assumption | What to check | Expected (as assumed) | Basis | Confirmed |",
        "|---|---|---|---|---|",
    ]
    for c in checklist():
        lines.append(
            f"| {c['assumption']} | {c['what_to_check']} | {c['expected']} | {c['basis']} | open |"
        )
    return "\n".join(lines) + "\n"
