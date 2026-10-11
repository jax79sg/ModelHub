"""Claude Code usage tracker: how much Claude Code was used to build this project.

Usage:
    python tools/claude_usage.py                          print the summary
    python tools/claude_usage.py --snapshot docs/claude-usage.json --update-readme README.md

It reads the conversation files Claude Code keeps on this computer for the project
(~/.claude/projects/<project>/). Only numbers are read out of them (token counts, costs,
timestamps); no prompt or reply text is ever copied. Claude Code deletes old conversation files
after a while, so `--snapshot` keeps the numbers in a file you can commit; sessions whose files
have since been deleted stay in it.

Cost is Claude Code's own running estimate (the `cost-state` records in the file), not a bill.
Days are UTC dates. Only this computer is seen: work done elsewhere is not counted.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

START, END = "<!-- usage:start -->", "<!-- usage:end -->"
KINDS = ("input", "output", "cache_read", "cache_write")


def project_dir(cwd: Path, home: Path | None = None) -> Path:
    """Where Claude Code keeps the conversations for a project folder."""
    home = home or Path.home()
    return home / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(cwd))


def _entries(path: Path):
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                entry = json.loads(line)
            except ValueError:
                continue  # a half-written last line
            if isinstance(entry, dict):
                yield entry


def _is_person_prompt(entry: dict) -> bool:
    if entry.get("isMeta") or entry.get("isSidechain"):
        return False
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return bool(content.strip())
    if isinstance(content, list):
        kinds = {block.get("type") for block in content if isinstance(block, dict)}
        return "text" in kinds and "tool_result" not in kinds
    return False


def _blank_tokens() -> dict:
    return {"input": 0, "output": 0, "thinking": 0, "cache_read": 0, "cache_write": 0}


def _segments(path: Path) -> list[dict]:
    """The final cost record of each stretch of a session. A resumed session can start its
    running total again from zero, so a drop means the earlier stretch is finished."""
    finished, current = [], None
    for entry in _entries(path):
        if entry.get("type") != "cost-state":
            continue
        if current is not None and entry.get("totalCostUSD", 0) < current.get("totalCostUSD", 0):
            finished.append(current)
        current = entry
    if current is not None:
        finished.append(current)
    return finished


def read_session(path: Path) -> dict:
    """Numbers for one session: its file, plus the helper-agent files kept beside it."""
    path = Path(path)
    responses: dict[tuple, tuple] = {}
    stamps: list[str] = []
    prompts = 0
    files = [path, *sorted((path.parent / path.stem).glob("subagents/*.jsonl"))]
    for file in files:
        for entry in _entries(file):
            stamp = entry.get("timestamp")
            if isinstance(stamp, str):
                stamps.append(stamp)
            if entry.get("type") == "user" and file == path and _is_person_prompt(entry):
                prompts += 1
            message = entry.get("message")
            if entry.get("type") != "assistant" or not isinstance(message, dict):
                continue
            tokens = message.get("usage")
            if not isinstance(tokens, dict):
                continue
            key = (message.get("id"), entry.get("requestId"))
            seen = responses.get(key)
            if seen is None or tokens.get("output_tokens", 0) >= seen[2].get("output_tokens", 0):
                responses[key] = (str(stamp or "")[:10], message.get("model") or "unknown", tokens)

    days: dict[str, dict] = defaultdict(lambda: {"responses": 0, **{k: 0 for k in KINDS}})
    seen_models: dict[str, dict] = defaultdict(_blank_tokens)
    for day, model, tokens in responses.values():
        row = days[day]
        row["responses"] += 1
        parts = {
            "input": tokens.get("input_tokens", 0),
            "output": tokens.get("output_tokens", 0),
            "cache_read": tokens.get("cache_read_input_tokens", 0),
            "cache_write": tokens.get("cache_creation_input_tokens", 0),
        }
        for kind, count in parts.items():
            row[kind] += count
            seen_models[model][kind] += count

    segments = _segments(path)
    models: dict[str, dict] = {}
    cost = api_ms = added = removed = 0
    for state in segments:
        cost += state.get("totalCostUSD", 0)
        api_ms += state.get("totalAPIDuration", 0)
        added += state.get("totalLinesAdded", 0)
        removed += state.get("totalLinesRemoved", 0)
        for model, used in (state.get("modelUsage") or {}).items():
            row = models.setdefault(model, {**_blank_tokens(), "cost_usd": 0.0})
            row["input"] += used.get("inputTokens", 0)
            row["output"] += used.get("outputTokens", 0)
            row["thinking"] += used.get("thinkingTokens", 0)
            row["cache_read"] += used.get("cacheReadInputTokens", 0)
            row["cache_write"] += used.get("cacheCreationInputTokens", 0)
            row["cost_usd"] += used.get("costUSD", 0)
    if not segments:  # no cost record: the replies still give token counts
        models = {name: {**row, "cost_usd": None} for name, row in seen_models.items()}

    return {
        "session": path.stem,
        "first": min(stamps) if stamps else None,
        "last": max(stamps) if stamps else None,
        "prompts": prompts,
        "cost_usd": round(cost, 4) if segments else None,
        "api_seconds": round(api_ms / 1000, 1),
        "lines_added": added,
        "lines_removed": removed,
        "models": models,
        "days": dict(sorted(days.items())),
    }


def merge_snapshot(old: dict, new: dict) -> dict:
    """Sessions seen now replace their older numbers; sessions no longer on disk are kept."""
    return {**old, **new}


def summarise(sessions: dict) -> dict:
    tokens = _blank_tokens()
    models: dict[str, dict] = {}
    days: dict[str, dict] = {}
    cost, unknown, api_seconds, prompts, added, removed = 0.0, 0, 0.0, 0, 0, 0
    firsts, lasts = [], []
    for record in sessions.values():
        prompts += record.get("prompts", 0)
        api_seconds += record.get("api_seconds", 0)
        added += record.get("lines_added", 0)
        removed += record.get("lines_removed", 0)
        if record.get("cost_usd") is None:
            unknown += 1
        else:
            cost += record["cost_usd"]
        if record.get("first"):
            firsts.append(record["first"])
        if record.get("last"):
            lasts.append(record["last"])
        for name, row in record.get("models", {}).items():
            total = models.setdefault(name, {**_blank_tokens(), "cost_usd": 0.0})
            for kind in tokens:
                total[kind] += row.get(kind, 0)
                tokens[kind] += row.get(kind, 0)
            if row.get("cost_usd") is not None:
                total["cost_usd"] += row["cost_usd"]
        for day, row in record.get("days", {}).items():
            total = days.setdefault(day, {"day": day, "responses": 0, **{k: 0 for k in KINDS}})
            for key in ("responses", *KINDS):
                total[key] += row.get(key, 0)
    ordered = sorted(days.values(), key=lambda d: d["day"])
    return {
        "sessions": len(sessions),
        "sessions_without_cost": unknown,
        "prompts": prompts,
        "cost_usd": round(cost, 2),
        "api_hours": round(api_seconds / 3600, 2),
        "lines_added": added,
        "lines_removed": removed,
        "tokens": tokens,
        "models": dict(sorted(models.items())),
        "days": ordered,
        "first_day": (min(firsts)[:10] if firsts else None),
        "last_day": (max(lasts)[:10] if lasts else None),
    }


def _n(value: float) -> str:
    return f"{value:,.0f}"


def render_markdown(summary: dict, generated: str | None = None) -> str:
    generated = generated or datetime.now(timezone.utc).strftime("%d %B %Y")
    t = summary["tokens"]
    lines = [
        (
            f"_Snapshot taken {generated}. Cost is Claude Code's own running estimate, not a "
            "bill; days are UTC; only work on the computer that built this is counted._"
        ),
        "",
        "| Measure | Value |",
        "|---|---|",
        f"| Sessions | {summary['sessions']} |",
        (
            f"| Days with activity | {len(summary['days'])} "
            f"({summary['first_day']} to {summary['last_day']}) |"
        ),
        f"| Messages typed by a person (approximate) | {_n(summary['prompts'])} |",
        f"| Estimated cost | ${summary['cost_usd']:,.2f} |",
        f"| Time Claude spent working (API) | {summary['api_hours']:.1f} hours |",
        (
            f"| Lines added / removed in files | {_n(summary['lines_added'])} / "
            f"{_n(summary['lines_removed'])} |"
        ),
        f"| Tokens read fresh / written | {_n(t['input'])} / {_n(t['output'])} |",
        (
            f"| Tokens read from cache / written to cache | {_n(t['cache_read'])} / "
            f"{_n(t['cache_write'])} |"
        ),
    ]
    if summary["sessions_without_cost"]:
        lines.append(
            f"| Sessions with no cost record | {summary['sessions_without_cost']} "
            "(tokens counted, cost left out) |"
        )
    lines += [
        "",
        "| Model | Cost | Fresh in | Out | Cache read | Cache write |",
        "|---|---|---|---|---|---|",
    ]
    for name, row in summary["models"].items():
        lines.append(
            f"| `{name}` | ${row['cost_usd']:,.2f} | {_n(row['input'])} | {_n(row['output'])} | "
            f"{_n(row['cache_read'])} | {_n(row['cache_write'])} |"
        )
    lines += [
        "",
        "| Day (UTC) | Replies | Fresh in | Out | Cache read | Cache write |",
        "|---|---|---|---|---|---|",
    ]
    for row in summary["days"]:
        lines.append(
            f"| {row['day']} | {_n(row['responses'])} | {_n(row['input'])} | {_n(row['output'])} | "
            f"{_n(row['cache_read'])} | {_n(row['cache_write'])} |"
        )
    lines += [
        "",
        (
            "_The per-day table counts the replies stored in the conversation file. Calls to the "
            "small helper model are only in Claude Code's own totals above, so the days add up to "
            "less than the totals._"
        ),
    ]
    return "\n".join(lines)


def update_readme(readme: Path, block: str) -> bool:
    """Replace what sits between the two markers. Returns False, touching nothing, if absent."""
    text = Path(readme).read_text(encoding="utf-8")
    if START not in text or END not in text:
        return False
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    Path(readme).write_text(f"{head}{START}\n{block}\n{END}{tail}", encoding="utf-8")
    return True


def collect(folder: Path) -> dict:
    return {
        path.stem: read_session(path)
        for path in sorted(Path(folder).glob("*.jsonl"))
        if path.is_file()
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument(
        "--project", type=Path, default=Path.cwd(), help="project folder (default: here)"
    )
    ap.add_argument(
        "--conversations", type=Path, help="folder of conversation files, if not the usual place"
    )
    ap.add_argument("--snapshot", type=Path, help="JSON file that keeps the numbers over time")
    ap.add_argument("--update-readme", type=Path, help="README to fill between the usage markers")
    args = ap.parse_args(argv)

    folder = args.conversations or project_dir(args.project.resolve())
    found = collect(folder) if folder.is_dir() else {}
    if not found and not (args.snapshot and args.snapshot.exists()):
        print(f"No Claude Code conversations found in {folder}", file=sys.stderr)
        return 2
    sessions = found
    if args.snapshot:
        old = (
            json.loads(args.snapshot.read_text(encoding="utf-8")) if args.snapshot.exists() else {}
        )
        sessions = merge_snapshot(old.get("sessions", {}), found)
        args.snapshot.parent.mkdir(parents=True, exist_ok=True)
        args.snapshot.write_text(
            json.dumps({"sessions": sessions}, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    block = render_markdown(summarise(sessions))
    if args.update_readme:
        if not update_readme(args.update_readme, block):
            print(f"{args.update_readme} has no {START} / {END} markers", file=sys.stderr)
            return 2
        print(f"Updated {args.update_readme}")
    else:
        print(block)
    return 0


if __name__ == "__main__":
    sys.exit(main())
