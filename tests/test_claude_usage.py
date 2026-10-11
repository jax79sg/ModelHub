"""The Claude Code usage tracker (tools/claude_usage.py): numbers only, never conversation text."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load():
    spec = importlib.util.spec_from_file_location(
        "claude_usage", ROOT / "tools" / "claude_usage.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def usage(inp=1, out=10, read=100, write=5):
    return {
        "input_tokens": inp,
        "output_tokens": out,
        "cache_read_input_tokens": read,
        "cache_creation_input_tokens": write,
    }


def reply(msg_id, request_id, when, tokens, model="claude-sonnet-5-5"):
    return {
        "type": "assistant",
        "timestamp": when,
        "requestId": request_id,
        "sessionId": "s1",
        "message": {"id": msg_id, "model": model, "usage": tokens},
    }


def prompt(text, when="2026-10-09T06:00:00.000Z"):
    return {"type": "user", "timestamp": when, "message": {"role": "user", "content": text}}


def tool_result(when="2026-10-09T06:00:05.000Z"):
    block = [{"type": "tool_result", "tool_use_id": "t", "content": "ok"}]
    return {"type": "user", "timestamp": when, "message": {"role": "user", "content": block}}


def cost_state(cost, **extra):
    state = {
        "type": "cost-state",
        "sessionId": "s1",
        "totalCostUSD": cost,
        "totalAPIDuration": 2000,
        "totalLinesAdded": 10,
        "totalLinesRemoved": 1,
        "modelUsage": {
            "claude-sonnet-5-5": {
                "inputTokens": 5,
                "outputTokens": 50,
                "thinkingTokens": 7,
                "cacheReadInputTokens": 500,
                "cacheCreationInputTokens": 25,
                "costUSD": cost,
            }
        },
    }
    state.update(extra)
    return state


def write_jsonl(path, entries):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")


def test_the_project_folder_name_follows_claude_codes_rule():
    mod = load()
    home = Path("/h")
    assert mod.project_dir(Path("/Users/jax/projects/modelhub"), home) == (
        home / ".claude" / "projects" / "-Users-jax-projects-modelhub"
    )


def test_a_response_repeated_while_streaming_is_counted_once_at_its_final_size(tmp_path):
    mod = load()
    path = tmp_path / "s1.jsonl"
    write_jsonl(
        path,
        [
            reply("m1", "r1", "2026-10-09T06:00:01.000Z", usage(out=3)),
            reply("m1", "r1", "2026-10-09T06:00:02.000Z", usage(out=40)),
            reply("m2", "r2", "2026-10-09T06:00:09.000Z", usage(out=10)),
        ],
    )
    record = mod.read_session(path)
    day = record["days"]["2026-10-09"]
    assert day["responses"] == 2 and day["output"] == 50


def test_days_are_split_by_date_and_tokens_are_kept_by_kind(tmp_path):
    mod = load()
    path = tmp_path / "s1.jsonl"
    write_jsonl(
        path,
        [
            reply("m1", "r1", "2026-10-09T23:00:00.000Z", usage(1, 10, 100, 5)),
            reply("m2", "r2", "2026-10-10T01:00:00.000Z", usage(2, 20, 200, 6)),
        ],
    )
    days = mod.read_session(path)["days"]
    assert days["2026-10-09"] == {
        "responses": 1, "input": 1, "output": 10, "cache_read": 100, "cache_write": 5,
    }  # fmt: skip
    assert days["2026-10-10"]["cache_read"] == 200


def test_people_prompts_are_counted_but_tool_results_are_not(tmp_path):
    mod = load()
    path = tmp_path / "s1.jsonl"
    write_jsonl(path, [prompt("do it"), tool_result(), prompt("then this"), tool_result()])
    assert mod.read_session(path)["prompts"] == 2


def test_cost_comes_from_claude_codes_own_cost_record_and_the_last_one_wins(tmp_path):
    mod = load()
    path = tmp_path / "s1.jsonl"
    write_jsonl(path, [cost_state(1.0), cost_state(4.5, totalLinesAdded=40)])
    record = mod.read_session(path)
    assert record["cost_usd"] == 4.5 and record["lines_added"] == 40
    model = record["models"]["claude-sonnet-5-5"]
    assert model["output"] == 50 and model["thinking"] == 7 and model["cache_read"] == 500


def test_a_restarted_total_adds_to_the_earlier_one_instead_of_replacing_it(tmp_path):
    mod = load()
    path = tmp_path / "s1.jsonl"
    write_jsonl(path, [cost_state(3.0), cost_state(5.0), cost_state(0.5), cost_state(2.0)])
    record = mod.read_session(path)
    assert record["cost_usd"] == 7.0  # 5.0 before the restart, 2.0 after
    assert record["models"]["claude-sonnet-5-5"]["output"] == 100


def test_helper_agent_files_beside_the_session_are_included(tmp_path):
    mod = load()
    path = tmp_path / "s1.jsonl"
    write_jsonl(path, [reply("m1", "r1", "2026-10-09T06:00:01.000Z", usage(out=10))])
    write_jsonl(
        tmp_path / "s1" / "subagents" / "agent-x.jsonl",
        [reply("a1", "q1", "2026-10-09T06:00:02.000Z", usage(out=7))],
    )
    assert mod.read_session(path)["days"]["2026-10-09"]["output"] == 17


def test_without_a_cost_record_tokens_still_count_and_cost_is_unknown(tmp_path):
    mod = load()
    path = tmp_path / "s1.jsonl"
    write_jsonl(path, [reply("m1", "r1", "2026-10-09T06:00:01.000Z", usage(out=10))])
    record = mod.read_session(path)
    assert record["cost_usd"] is None
    assert record["models"]["claude-sonnet-5-5"]["output"] == 10


def test_the_record_holds_no_conversation_text(tmp_path):
    mod = load()
    path = tmp_path / "s1.jsonl"
    write_jsonl(path, [prompt("my secret plan"), cost_state(1.0)])
    assert "secret" not in json.dumps(mod.read_session(path))


def test_a_snapshot_keeps_sessions_whose_transcripts_have_since_been_deleted():
    mod = load()
    old = {"gone": {"session": "gone", "cost_usd": 2.0}, "kept": {"session": "kept", "cost_usd": 1}}
    new = {"kept": {"session": "kept", "cost_usd": 3.0}}
    merged = mod.merge_snapshot(old, new)
    assert merged["gone"]["cost_usd"] == 2.0 and merged["kept"]["cost_usd"] == 3.0


def test_the_summary_adds_up_sessions_models_and_days():
    mod = load()
    sessions = {
        "a": {
            "session": "a", "first": "2026-10-09T06:00:00Z", "last": "2026-10-09T08:00:00Z",
            "prompts": 3, "cost_usd": 2.0, "api_seconds": 60.0, "lines_added": 10,
            "lines_removed": 1,
            "models": {"m": {"input": 1, "output": 2, "thinking": 0, "cache_read": 3,
                             "cache_write": 4, "cost_usd": 2.0}},
            "days": {"2026-10-09": {"responses": 2, "input": 1, "output": 2, "cache_read": 3,
                                    "cache_write": 4}},
        },
        "b": {
            "session": "b", "first": "2026-10-10T06:00:00Z", "last": "2026-10-10T07:00:00Z",
            "prompts": 1, "cost_usd": None, "api_seconds": 0.0, "lines_added": 0,
            "lines_removed": 0,
            "models": {"m": {"input": 10, "output": 20, "thinking": 0, "cache_read": 30,
                             "cache_write": 40, "cost_usd": None}},
            "days": {"2026-10-10": {"responses": 1, "input": 10, "output": 20, "cache_read": 30,
                                    "cache_write": 40}},
        },
    }  # fmt: skip
    total = mod.summarise(sessions)
    assert total["sessions"] == 2 and total["prompts"] == 4
    assert total["cost_usd"] == 2.0 and total["sessions_without_cost"] == 1
    assert total["tokens"]["output"] == 22 and total["tokens"]["cache_read"] == 33
    assert total["first_day"] == "2026-10-09" and total["last_day"] == "2026-10-10"
    assert [d["day"] for d in total["days"]] == ["2026-10-09", "2026-10-10"]
    assert total["api_hours"] == round(60.0 / 3600, 2)


def test_the_readme_block_is_replaced_between_its_markers_and_nothing_else(tmp_path):
    mod = load()
    readme = tmp_path / "README.md"
    readme.write_text("before\n<!-- usage:start -->\nold\n<!-- usage:end -->\nafter\n")
    mod.update_readme(readme, "NEW BLOCK")
    text = readme.read_text()
    assert "NEW BLOCK" in text and "old" not in text
    assert text.startswith("before\n") and text.endswith("after\n")


def test_a_readme_without_markers_is_left_alone_and_the_problem_is_reported(tmp_path):
    mod = load()
    readme = tmp_path / "README.md"
    readme.write_text("nothing here\n")
    assert mod.update_readme(readme, "X") is False
    assert readme.read_text() == "nothing here\n"
