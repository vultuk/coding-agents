---
name: dashboard-designer
description: Design, review, and implement dashboard UX and layout improvements using an embedded offline ruleset for KPI prioritization, visual hierarchy, chart choice, interaction design, and accessibility. Use when asked to add or modify dashboard widgets/cards, reorganize dashboard pages, improve data-dense interfaces, or audit dashboards against best practices.
---

# Dashboard Designer

Design dashboards that are easy to scan, useful for decisions, and maintainable in real codebases.

Use this skill when a user asks for changes like:
- "Use `$dashboard-designer` to add a new widget to `/dashboard` showing how many clients we currently have."
- "Refactor this dashboard so top KPIs are clearer."
- "Review this dashboard page for UX and data-viz issues."
- "Make this dashboard mobile-friendly without losing critical insight."

## Use Embedded References Only

Load `references/dashboard-designer-playbook.md` first.

Load these source notes when deeper rationale is needed:
- `references/geckoboard-guide-embedded.md`
- `references/adriel-layout-principles-embedded.md`
- `references/pencil-and-paper-patterns-embedded.md`
- `references/justinmind-dashboard-practices-embedded.md`

Treat those local files as the skill's source of truth. Do not depend on remote article fetches during execution unless the user explicitly asks for fresh web research.

## Execution Workflow

1. Define intent before touching layout.
- Identify the exact decision the dashboard or widget should support.
- Identify audience and dashboard type (operational, analytical, strategic, or product-home).
- Write one sentence: "This widget helps <persona> decide <decision>."

2. Audit the current dashboard implementation.
- Inspect existing card count, hierarchy, and grouping.
- Identify overload, unclear labels, missing context, and weak interactions.
- Capture constraints from the actual code (UI library, breakpoints, API fields, loading states).

3. Design the change using the playbook.
- Apply the widget recipe and chart selection matrix in `dashboard-designer-playbook.md`.
- Place high-value KPIs first (top-left for LTR locales).
- Add context: deltas, thresholds, baselines, or targets.
- Keep visual consistency with existing design language unless user asks for redesign.

4. Implement in code.
- Make the minimum code changes needed to ship the improvement.
- Keep naming and component boundaries clear.
- Ensure interaction paths work (filtering, drill-down, details view, export if relevant).

5. Validate behavior and UX quality.
- Check desktop and mobile states.
- Verify loading, empty, and error states.
- Verify accessibility (contrast, not color-only signals, labels, keyboard if applicable).
- Run project tests/lint relevant to touched files.

6. Report outcome clearly.
- State what changed.
- Map each change to a dashboard principle from the embedded playbook.
- Flag any unresolved tradeoffs.

## Completion Contract

- Treat the task as incomplete until the changed dashboard elements, states, and validation checks are all covered or explicitly `[blocked]`.
- Before finalizing, verify that each new or changed widget answers one clear question and that its placement still matches the surrounding information hierarchy.

## Widget Addition Protocol

When asked to add a widget, always define these fields before implementation:

- `question`: what question this widget answers
- `primary_metric`: the headline value
- `time_scope`: now/today/7d/30d/custom
- `comparison`: previous period, target, benchmark, or threshold
- `visual_type`: KPI card, line, bar, table, or status block
- `drill_path`: where user goes for detail
- `states`: loading, empty, error
- `placement`: dashboard section and order

If any field is missing, infer from nearby dashboard patterns and document the assumption in your response.

## Quality Bar

Apply all of these:

- Lead with purpose and key KPI visibility.
- Keep default view focused and low-clutter.
- Group related metrics by objective or funnel stage.
- Use chart types users can parse quickly.
- Preserve consistency across cards and sections.
- Provide contextual cues (deltas, targets, thresholds).
- Support progressive disclosure with drill-down.
- Keep the dashboard actionable, not just descriptive.
- Keep iterating based on usage and feedback.

## Output Expectations

For implementation requests, deliver:
- Actual code changes
- A short rationale tied to playbook rules
- Validation results (tests/checks run, or what could not be run)

For review-only requests, return prioritized findings with concrete fixes and file references.
