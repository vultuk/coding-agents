# Compatibility Notes

This repository is written for both Claude Code and Codex-style coding agents.

## Codex Tool Mapping

- `Task(subagent_type="Bash", ...)`
  Use `functions.exec_command` for a single shell task, or `multi_tool_use.parallel` when the shell reads are independent and can run concurrently.
- `Task(subagent_type="Explore", ...)`
  Use local inspection first. When a bounded sidecar exploration task helps, use `spawn_agent` with the `explorer` role.
- `Task(subagent_type="Plan", ...)`
  Use `functions.update_plan` or keep the plan local in the main run.
- `Task(subagent_type="general-purpose", ...)`
  Keep the work local unless there is a clear, bounded sidecar task. If delegation helps, use `spawn_agent`.

## Editing Rules

- Use `apply_patch` for manual file edits.
- Use `functions.exec_command` for formatting, tests, builds, and other terminal commands.
- Do not simulate patching or editing inside bash when a direct edit tool is available.

## Verification Rules

- Treat retrieval, planning, execution, and verification as separate phases.
- Before finalizing, confirm the requested output contract, grounding, and any completion checks.
- Before irreversible or externally visible actions, run a short pre-flight summary and verify the target parameters.
