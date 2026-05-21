---
name: issue-writer
description: Write concise, eval-driven GitHub issues for agentic coding workflows when Codex needs to turn a rough request into a short implementation issue without an ExecPlan. Use when drafting issues that should stay outcome-focused, preserve existing behaviour, and define success through observable evals.
---

# Issue Writer

## Overview

Write short GitHub issues that an implementation agent can act on quickly. Keep the issue focused on the problem, the desired outcome, and observable evals rather than solution design.

## Workflow

1. Infer the real change the user wants, even if the request is rough.
2. Keep the title short, specific, and area-first when possible.
3. Write a tight problem statement grounded in the user's pain.
4. Describe the end state in outcome terms.
5. Add only the functional requirements that matter.
6. Define success with externally observable evals.
7. Add minimal notes only when scope or reuse guidance is genuinely useful.

## Issue Shape

Use this structure unless the user asks for something else:

```markdown
# <Short issue title>

## Summary

<One or two sentences describing the change>

## Problem

<Why this matters and what is wrong today>

## Desired outcome

<What should be true once this is done>

## Requirements

- <Short requirement>
- <Short requirement>
- <Short requirement>

## Evals

- <Observable check>
- <Observable check>
- <Observable check>
- <Regression check>

## Notes

- <Scope or implementation guidance only if genuinely useful>
- <Mention reuse of existing logic if relevant>

## Writing Rules

- Keep the issue tight and practical.
- Focus on the problem, desired outcome, and observable behaviour.
- Let the implementation agent infer most technical detail.
- Use evals as the main definition of done.
- Preserve existing behaviour unless the request explicitly changes it.
- Avoid speculative architecture unless the user asks for it.
- Avoid unnecessary edge cases unless they are central to the request.
- Do not write an ExecPlan inside the issue.

## Title Rules

- Keep the title short and specific.
- Start with the area first when possible.
- Prefer formats like `MAM Detail: Show master balance and summed slice balances`.

## Section Guidance

- `Summary`: use one or two sentences only.
- `Problem`: explain the operational pain clearly and stay grounded in what was said.
- `Desired outcome`: state the end state plainly and outcome-first.
- `Requirements`: keep bullets short and functional.
- `Evals`: make every bullet externally observable and include a regression check when relevant.
- `Notes`: keep this section light and include only useful scope or reuse guidance.

## What To Avoid

- Long design docs.
- PRD-style background.
- Detailed architecture.
- Generic engineering filler.
- Excessive edge-case lists.
- Extra headings that do not help the reader.

## Output Standard

Return only the issue body in Markdown unless the user explicitly asks for commentary or extra context.
