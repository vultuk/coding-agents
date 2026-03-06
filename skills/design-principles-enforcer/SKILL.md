---
name: design-principles-enforcer
description: Enforce strict, language-agnostic software design principles through structured audits and remediation plans. Use when asked to review architecture or implementation quality, check SOLID/DRY/KISS/LoD/DbC/CQS compliance, prevent design regressions during feature work, or produce a pass/fail design-principles report for files, modules, or whole repositories.
---

# Design Principles Enforcer

## Overview

Enforce explicit, verifiable standards instead of broad style opinions. Produce evidence-backed findings, strict pass/fail outcomes, and prioritized remediation actions.

Use [references/design-principles-matrix.md](references/design-principles-matrix.md) for principle-specific checks and acceptance criteria.

## Enforcement Workflow

1. Define scope.
   Analyze the requested target (file, module, service, or repository) and identify the architectural boundary to review.
2. Build an inventory.
   Map modules/components, public interfaces, dependencies, state mutation points, and cross-module call chains.
3. Evaluate each principle.
   Apply every principle in the matrix and collect concrete code evidence for each pass/fail judgment.
4. Classify findings by severity.
   Assign:
   - `P0`: correctness/safety risks or guaranteed design breakage
   - `P1`: high-impact maintainability or extensibility failure
   - `P2`: medium quality or consistency degradation
   - `P3`: low-priority improvement
5. Propose minimum viable remediation.
   Recommend the smallest change-set that restores compliance while limiting regression risk.
6. Re-check compliance after edits.
   Re-run the same matrix and report deltas: `fixed`, `remaining`, `new`.

## Strictness Rules

- Enforce by default; do not waive violations without explicit rationale.
- Treat "not applicable" as valid only when the architecture truly lacks the relevant construct.
  - Example: mark LSP/ISP as `N/A` when no inheritance or interface hierarchy exists.
- Require evidence for every judgment.
  - Include file paths, affected symbols, and behavioral impact.
- Reject hand-wavy conclusions.
  - Replace vague language ("could be cleaner") with objective failure criteria.
- Prefer behavior-preserving fixes first.
  - Refactor structure before changing external behavior unless behavior itself violates a principle.

## Output Contract

Produce four sections in this order:

1. `Scope`
   Include reviewed paths/components and assumptions.
2. `Compliance Scorecard`
   List each principle as `PASS`, `FAIL`, or `N/A` with one-sentence evidence.
3. `Findings`
   Order by severity (`P0` to `P3`). For each finding, include:
   - violated principle
   - concrete evidence
   - impact
   - minimal fix
4. `Remediation Plan`
   Provide a sequenced implementation plan with verification steps and expected compliance deltas.

## Generality Constraints

- Keep the skill language-agnostic.
- Do not enforce Rust-only idioms or compiler-specific rules.
- When language/runtime differences affect interpretation, enforce intent-equivalent checks rather than syntax-specific checks.
- Framework-specific checks are allowed when they operationalize a general principle.
  - For React UI work, treat matching Storybook stories for newly created components as required self-documenting evidence.
