---
name: prompt-optimizer
description: Rewrite rough prompts, prompt fragments, workflow notes, or existing system/developer/user instructions into stronger GPT-5.4-style prompts with explicit output contracts, grounding rules, tool guidance, completion criteria, and verification loops. Use when the user asks to improve, polish, migrate, compress, formalize, or "make better" a prompt for agents, research, coding, structured output, or customer-facing writing.
---

# Prompt Optimizer

Turn incomplete prompt drafts into cleaner, stronger prompts that are easier for GPT-5.4-style models and agents to follow reliably.

Load [references/block-library.md](references/block-library.md) when you need reusable block wording or task-shape-specific sections.

## Workflow

1. Classify the prompt shape.
   Choose the smallest fitting category:
   - general execution
   - coding or terminal agent
   - research or synthesis
   - strict structured output
   - customer-facing writing
   - prompt-stack update (system/developer/user blocks)

2. Extract the real contract from the user input.
   Identify:
   - objective
   - inputs and available context
   - required output
   - tool expectations
   - side effects
   - what counts as done
   - missing but retrievable context

3. Improve the prompt without changing the task.
   Keep the user's intent, constraints, and tone unless they are unclear or conflicting.
   Add only the blocks that materially improve reliability.

4. Add the minimum useful control blocks.
   Common high-value additions:
   - output contract
   - follow-through or permission rules
   - grounding or citation rules
   - dependency checks or tool persistence
   - completeness contract
   - verification loop
   - structured output contract
   - action safety
   - user update rules for long-running agents

5. Remove bloat.
   Delete repetition, vague aspirations, redundant style notes, and blocks that do not help the task shape.

6. Return the optimized prompt.
   Default to giving the finished prompt first.
   Add a short notes section only when it materially helps the user understand the changes.

## Rewrite Rules

- Preserve the task. Improve the contract.
- Prefer concise, enforceable language over motivational wording.
- Prefer exact outputs over generic "be thorough" instructions.
- Prefer evidence, grounding, and explicit verification over increasing reasoning effort by default.
- Do not add research, citations, or tool requirements unless the task needs them.
- Do not force every available block into every prompt.
- When the user asks for a compact prompt, compress aggressively but keep the output, grounding, and completion rules that matter most.

## Task-Shape Guidance

### General Execution

- Add a clear output contract.
- Add a default follow-through rule when the task is low-risk and reversible.
- Add a verification loop when the task has several deliverables or hidden failure modes.

### Coding or Terminal Agent

- Keep tool boundaries explicit.
- Add dependency-aware sequencing.
- Add completion and verification rules so the prompt does not stop at analysis.
- Prefer narrow, concrete validation expectations over "test everything".

### Research or Synthesis

- Add source boundary, citation, and grounding rules.
- Add a retrieval plan only when evidence gathering matters.
- Require conflicts and inferences to be labeled explicitly.

### Strict Structured Output

- Require exact format-only output.
- Add schema, field, or bracket-balance checks.
- Require an explicit error object or clarification path when schema data is missing.

### Customer-Facing Writing

- Separate persistent persona from per-response writing controls.
- Keep channel, register, formatting bans, and length limits explicit.
- Do not let personality override hard output requirements.

### Prompt-Stack Update

- Preserve instruction priority explicitly.
- Keep scope local when the change is "for this turn only" or "for the next response only".
- State what changed, what still applies, and whether the update is temporary or persistent.

## Output Contract

Default response:

1. `Optimized Prompt`
   Return the rewritten prompt in a fenced code block.
2. `Why This Version`
   Return 3-6 short bullets only when useful.

If the user asks for only the finished prompt, return only the prompt block.
If useful, append one short `Tuning Notes` section with recommended `reasoning_effort` or verbosity settings.

## Quality Bar

Before finalizing, verify that the rewritten prompt:

- preserves the user's real goal,
- makes the output format explicit,
- adds only relevant control blocks,
- handles side effects and missing context correctly,
- defines what "done" means,
- is shorter or clearer than the original unless extra detail is genuinely required.
