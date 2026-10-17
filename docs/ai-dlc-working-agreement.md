# Working with AI-DLC: what keeps work on the loop

In the enterprise build, work carried on for two days after a plan was approved without one call to the engine
(`aidlc engine orchestrate next` / `report`). Seven units were built and merged outside the per-unit
directives, receipts and checkpoints. The audit log shows it: after `PLAN_APPROVAL_RECORDED` (2026-10-15) there is no engine
call until 2026-10-17. These are the rules and checks that stop it happening again.

## The rule

Nothing is committed, pushed, merged, or written into the project's source, tests, deploy, docs or workflow folders unless the
AI-DLC engine's latest directive covers it. Work the workflow does not cover is raised with the person first, never done quietly.
An approved plan is an approval of that plan, not permission to stop asking the engine what comes next.

## What is enforced now

| Check | Where | What it does |
|---|---|---|
| Loop guard | `.claude/loop/loop_guard.py`, a `PreToolUse` hook in `.claude/settings.json` | Blocks `git commit/push/merge`, `gh pr create/merge/edit`, the GitHub merge API and writes to `src/ server/ web/ deploy/ tests/ docs/ .github/ tools/ packaging/ README.md pyproject.toml` when the active intent's `.aidlc-engine/engine-touch` marker (touched by every advancing `next` and `report`, not by read-only calls like `status`) is older than 30 minutes. The block message says to run `aidlc engine orchestrate next --resume`. Reading, testing and `aidlc ...` commands are never blocked. Limit: `AIDLC_LOOP_MAX_AGE_MINUTES`. |
| Status line | `.claude/loop/status_line.py` (wraps `aidlc engine statusline`) | Shows "engine asked Nm ago" and a warning once it passes the limit, so drift is visible at a glance. |
| Tests | `tests/test_loop_guard.py` | The guard and the status line are tested. |
| Standing rule | `.claude/CLAUDE.md` ("Working agreement") | Reloaded every session, so it survives context compaction. |
| Pull request template | `.github/pull_request_template.md` | Every PR names its AI-DLC stage, unit and the last engine call. |

The guard proves the engine was asked recently, not that its answer was followed; a person reading the status line and the PR
template is the other half.

## For the next intent (set up when it starts)

1. **Turn the framework's own guards on.** The current intent runs with `Guard Policy: off` (set by the `classic` scope and kept by
   the tailored plan). Ask for `strict` at the start: `aidlc engine config set guard-policy strict`. Check `aidlc engine status` shows it.
2. **Approve one plan per unit, not one plan for the whole stage.** A stage-level approval left the engine counting seven unit
   work items it never emitted directives for. With per-unit plans every unit gets its directive, receipts, checkpoint and
   completion approval, and each pull request is one unit.
3. **One PR per engine step**, with the PR template filled in. A CI job that fails a PR with an empty AI-DLC field can follow
   once the field has been used on a few PRs.
4. **Say where the work stands at the start of each report**: stage, unit, last engine call.
