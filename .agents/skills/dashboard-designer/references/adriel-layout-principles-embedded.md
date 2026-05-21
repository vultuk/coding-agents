# Adriel Layout Principles (Embedded Notes)

Source captured locally from:
- `https://www.adriel.com/blog/the-anatomy-of-a-great-dashboard-layout-tips-from-real-teams`

Captured on: 2026-03-05 (text snapshot)

## High-Level Thesis

Dashboard layout is not cosmetic. Layout quality changes decision quality, alignment speed, and response time across teams.

## Five Principles from the Article

1. Start with the question, not the data.
- Define decisions first.
- Select KPIs that move goals, not merely available metrics.
- Tailor KPI sets by audience (executive vs performance operator).

2. Group metrics by funnel stage or objective.
- Typical group model:
- Awareness: impressions, reach, CPM
- Engagement: CTR, landing-page conversion
- Revenue/outcome: CPA, ROAS, pipeline value
- Place campaign summary first, then deeper conversion/ROI diagnostics.

3. Use visual hierarchy to drive focus.
- Not all KPIs are equal.
- Emphasize key KPIs with stronger placement/size.
- Avoid equal-weight grids that hide signal in noise.

4. Combine cross-channel data in one view.
- Do not stop at siloed channel outcomes.
- Tie spend and activity to business outcomes across channels.
- Prevent local optimization that harms system-level performance.

5. Make dashboards interactive, not static.
- Enable filtering, segmentation, and drill-down.
- Support fast movement from overview to detail without exporting data.

## Bonus Direction

Use assistant/AI-style querying where available to accelerate interpretation and anomaly detection, but keep core layout and data semantics clear even without AI.

## Implementation Cues

- Treat every section as decision support, not a report dump.
- Favor traceability from top KPI to root-cause detail.
- Ensure interactions preserve context and reduce navigation friction.

