# Pencil & Paper Patterns (Embedded Notes)

Source captured locally from:
- `https://www.pencilandpaper.io/articles/ux-pattern-analysis-data-dashboards`

Captured on: 2026-03-05 (text snapshot)

## Key Framing

Dashboard UX is a full interaction system, not just a chart canvas. Good outcomes require strong data understanding, realistic user context, and intentional interaction patterns.

## Upfront Discovery Prompts

Use these questions early:
- Is the underlying data clean, consistent, and scalable?
- What historical depth exists?
- What insights can be derived from existing fields?
- Which personas share enough needs for one default view?
- Which actions and warnings deserve priority in overview state?
- Which insights currently take users too long to compile manually?

## Dashboard Experience Types

- Reporting: summarize and tell a coherent data story.
- Monitoring: surface real-time anomalies and warnings.
- Exploration/discovery: support flexible interrogation of data.
- Functional/integrated: guide ongoing task focus.
- Product home/dashboard: provide orientation plus navigation.

## Interaction Anatomy

Navigation:
- Reduce navigation friction before users enter analysis mode.

Orientation:
- Provide immediate understanding of what users are seeing and where to go next.

Filtering:
- Prioritize default filters with highest utility.
- Keep filter behavior predictable and visible.

Drill-down:
- Use drawers for contextual detail.
- Use details pages for deep, broad exploration.

Action execution:
- Support inline actions and multi-select workflows when needed.
- Provide explicit success/error feedback.

## Layout and Scanning Guidance

- Structure sections top-down by importance.
- For LTR reading patterns, prioritize left-side placement for critical metrics.
- Use consistent card layouts and recurring UI conventions.
- Start with global overview; allow deeper interaction paths.

## Chart and Data-Viz Guidance

- Use accessible color semantics; avoid color-only signals.
- Use line styles/textures where color differentiation is weak.
- Show deltas consistently to anchor interpretation.
- Manage label density with threshold rules, reduced ticks, and tooltips.
- Apply typographic hierarchy to emphasize critical numbers.

## Responsiveness Guidance

- Validate whether mobile users need full dashboard detail.
- Re-layout charts for mobile, do not merely shrink desktop.
- Offer orientation hints for complex views where needed.

## Common UX Problems and Remedies

Density disjoint:
- Too much information, weak hierarchy.
- Remedy: reduce default complexity and strengthen hierarchy.

Random/unfocused data:
- "We have it, so show it" behavior.
- Remedy: map each chart to a clear user need and action.

Missing comparisons/baselines:
- Data feels like disconnected numbers.
- Remedy: add deltas, benchmarks, historical anchors.

Jargon without explanation:
- Users cannot decode terms and acronyms.
- Remedy: titles, legends, tooltips, plain-language support.

Color-coding mishaps:
- Meaning is inconsistent or inaccessible.
- Remedy: semantic color system plus non-color cues.

## Important Operational Note

Allow raw data export pathways when appropriate so users can continue analysis outside the dashboard if needed.

