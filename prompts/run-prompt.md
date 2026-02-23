---
name: run-prompt
description: Log prompts to .prompts/log.md with metadata before executing user instructions. Provides audit trail of all prompts run in the repository.
arguments:
  - name: PROMPT
    required: true
    description: The prompt/instructions to log and then execute
---

# Run Prompt with Logging

Before executing the user-supplied prompt, first append a log entry to `.prompts/log.md`. If the path does not exist, create it.

## SubAgent Strategy

This is a **lightweight workflow** that typically doesn't require SubAgents for the logging phase. However, the `$PROMPT` execution phase may benefit from SubAgents depending on its complexity.

**Codex note:** Codex does not support `Task(...)` subagents. Use `functions.shell_command` and `multi_tool_use.parallel` to run the same commands, or run steps sequentially. For Explore/Plan tasks, use normal file searches and the plan tool. See [`../COMPATIBILITY.md`](../COMPATIBILITY.md).

### When to Use SubAgents

After logging, if the `$PROMPT` involves:
- **Codebase exploration**: Use `Task(subagent_type="Explore", ...)`
- **Multiple independent bash commands**: Use parallel `Task(subagent_type="Bash", ...)` calls
- **Complex planning**: Use `Task(subagent_type="Plan", ...)`

The logging itself is simple and should be executed directly without SubAgents.

## Logging Requirements

1. Create the `.prompts/` directory if needed. Never overwrite `log.md`; always append.

2. Write a single entry per run using the exact Markdown template below.

3. Use an ISO-8601 UTC timestamp (e.g., 2025-09-04T12:34:56Z).

4. Determine the user as follows:
   - If inside a Git repository, prefer `git config --get user.name` and `git config --get user.email` (if set)
   - If not available, fall back to the operating system user (e.g., `USER`, `whoami`)

5. Preserve the prompt text verbatim, including all whitespace and newlines.

6. Use a FOUR-backtick Markdown fence for the prompt block to avoid collisions if the prompt contains triple backticks.

7. If logging fails for any reason, stop and surface the error rather than executing the prompt.

## Markdown Entry Template

Fill in the bracketed placeholders exactly once per run:

```markdown
### [TIMESTAMP_UTC]
- user: [DISPLAY_NAME and optionally <email>]
````text
$PROMPT
````
```

## Execution

After the log entry has been appended successfully, execute exactly the instructions provided in `$PROMPT`.

## Example Log Entry

```markdown
### 2025-09-04T12:34:56Z
- user: John Smith <john@example.com>
````text
Review the authentication module for security issues
and create a report of findings.
````
```

## Privacy Note

The log file may contain sensitive information. Consider:
- Adding `.prompts/` to `.gitignore` if prompts contain sensitive data
- Reviewing logs before committing to version control
- Using this primarily for personal audit trails
