# Dashboard Designer Playbook (Embedded)

Primary execution guide for `dashboard-designer`.
Use this file first, then load source-specific files for deeper rationale.

## 1. Start With Decision Intent

Before designing or coding, define:
- `persona`: who uses this dashboard
- `dashboard_type`: operational, analytical, strategic, product-home
- `decision`: the specific decision this view should accelerate
- `action`: what the user should do after seeing the data

If you cannot express the dashboard purpose in one sentence, the scope is still unclear.

## 2. Core Principles (Unified Ruleset)

Apply these in order:
1. Prioritize purpose over volume: show only what supports the decision.
2. Lead with critical KPIs: place highest-value indicators in prime scan zones.
3. Group metrics by objective: funnel stage, workflow stage, team function, or domain.
4. Keep visual hierarchy explicit: size, position, contrast, and spacing signal importance.
5. Prefer fast-to-parse visuals: line, bar, KPI stat, concise table before novelty charts.
6. Provide context for every headline number: delta, baseline, target, threshold, or trend.
7. Reduce noise: remove decorative UI that does not communicate data.
8. Keep labels short and unambiguous for the target audience.
9. Use consistent card structure and visual language across sections.
10. Enable progressive disclosure: overview first, drill-down second.
11. Keep dashboards actionable: expose warnings, anomalies, and next-step paths.
12. Iterate continuously based on usage and feedback.

## 3. Widget Recipe

For each new widget, define:
- `question`: What question does this widget answer?
- `metric`: What single metric is the headline?
- `scope`: What time range and filters apply by default?
- `comparison`: Previous period, target, benchmark, or threshold.
- `visual`: KPI, line, bar, table, status list, or hybrid.
- `interaction`: tooltip, legend toggle, filter, drill, detail pane, or details page.
- `placement`: section and order within dashboard hierarchy.
- `state_model`: loading, empty, error, partial data.
- `refresh`: static snapshot, periodic refresh, or live/near-live.

Do not implement until all fields are defined or inferred.

## 4. Layout and Information Architecture

Use this placement order for LTR interfaces:
1. Top-left: summary KPI cards for immediate orientation.
2. Upper band: global health and alert-level indicators.
3. Middle: trend and comparison charts.
4. Lower: detailed tables and secondary breakdowns.

Layout guidelines:
- Keep initial view near one screen when possible.
- Prefer 5-6 high-value cards in the initial viewport.
- Use sections/panels with clear headings.
- Keep spacing intentional; empty space improves scan speed.
- Use grid structure for alignment and predictable rhythm.

## 5. Chart Selection Matrix

Select visualization by user task:
- Single current value and status: KPI card with delta and color-safe indicator.
- Trend over time: line chart with sparing labels.
- Category comparison: bar chart.
- Ranked contribution: horizontal bar chart.
- Composition over time: stacked bar/area with careful legend clarity.
- Dense record-level detail: sortable table with concise columns.
- Threshold monitoring: status tiles or compact alerts list.

Avoid:
- Pie/area charts for precise comparisons when alternatives are clearer.
- Overly dense multi-series lines in default state.
- 3D or decorative chart styles.

## 6. Context and Number Formatting

For every primary metric:
- Show units.
- Round to practical precision.
- Show direction and magnitude of change.
- Add baseline or target where relevant.
- Add threshold warnings for abnormal states.

Formatting defaults:
- Use compact notation for large numbers (`1.2K`, `3.4M`) when readability improves.
- Avoid unnecessary decimal precision.
- Keep period labels explicit (`Today`, `Last 7 days`, `vs previous 7 days`).

## 7. Interaction Patterns

Recommended interaction stack:
1. Global filters for date/segment that affect the full page.
2. Card-level controls for local comparisons or variable toggles.
3. Tooltips/hover/focus for secondary details.
4. Drill-down into drawer or dedicated details page for deep analysis.
5. Export option for raw data where users need external workflows.

Interaction guardrails:
- Keep defaults useful; do not expose every variable initially.
- Make loading feedback explicit for filter and drill actions.
- Keep filter affordances discoverable and persistent.
- Preserve user context when returning from details views.

## 8. Accessibility and Responsiveness

Accessibility:
- Never encode status with color alone; add text/icon/pattern cues.
- Maintain sufficient contrast for text and chart marks.
- Label charts, legends, and controls clearly.
- Ensure keyboard interaction for critical controls where applicable.

Responsive behavior:
- Re-prioritize content for mobile instead of shrinking everything.
- Keep core KPIs and one core trend visible first.
- Move lower-priority detail to secondary screens or tabs.
- Consider landscape hints for complex charts when needed.

## 9. Common Anti-Patterns and Fixes

Anti-pattern: random metric pile.
Fix: force each widget to map to a concrete decision and objective group.

Anti-pattern: high data density with low comprehension.
Fix: reduce default series, reduce labels, use progressive disclosure.

Anti-pattern: no baselines or targets.
Fix: add deltas, historical comparisons, thresholds, and target markers.

Anti-pattern: inaccessible color coding.
Fix: add non-color signals and tighten semantic color usage.

Anti-pattern: technically correct but operationally useless view.
Fix: add alerts, prioritized anomalies, and explicit next-step links/actions.

## 10. Implementation Checklist

Use as final gate before completion:
- Purpose and persona are explicit.
- Widget questions are defined.
- KPI hierarchy is visible in layout.
- Grouping is logical and labeled.
- Visual choices match task semantics.
- Context (delta/target/baseline) is present for headline numbers.
- Interactions support drill-down without clutter.
- Empty/loading/error states are designed.
- Mobile behavior preserves top insights.
- Accessibility checks pass.
- Code style and tests are updated for touched files.

## 11. Prompt Patterns for This Skill

Use these structures when user intent is broad:

1. "Refactor dashboard for clarity"
- Audit existing cards and hierarchy.
- Remove low-value cards from default view.
- Re-group by objective.
- Add context and actionable states.

2. "Add a new KPI widget"
- Fill widget recipe.
- Implement card + context + drill path.
- Place according to hierarchy.

3. "Review dashboard UX"
- Run anti-pattern scan.
- Return prioritized findings and concrete fixes.

