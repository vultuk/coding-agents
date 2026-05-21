# Geckoboard Guide (Embedded Notes)

Source captured locally from:
- `/Users/vultuk/Downloads/geckoboard-dashboard-design-and-build-a-great-dashboard.pdf`

Captured on: 2026-03-05

## Core Checklist from the Guide

1. Define dashboard purpose before layout decisions.
2. Include only the most important content.
3. Improve data-ink ratio by removing non-data decoration.
4. Round numbers to practical precision.
5. Choose the most efficient visualization for quick understanding.
6. Group related metrics so users can find them quickly.
7. Keep chart/layout patterns consistent across sections.
8. Use size and position to communicate hierarchy.
9. Give numeric context (history, average, target, thresholds).
10. Use short, clear, audience-specific labels.
11. Allow tasteful rule-breaking only when it increases engagement.
12. Iterate continuously using real user feedback.

## Practical Translation for Implementation

Purpose:
- Require a clear "what decision does this support?" statement.

Content control:
- If critical content does not fit, split into multiple dashboards/views rather than cramming.

Data-ink ratio:
- Remove decorative backgrounds, extra grid lines, and redundant iconography.

Precision:
- Avoid noisy decimals when trend direction is the real signal.

Visualization:
- Prefer straightforward numerals, bars, lines, and concise tables.

Grouping:
- Group by campaign, region, team, product, funnel stage, or timeframe.

Hierarchy:
- Emphasize key widgets with position and size.
- For LTR interfaces, top-left is high-value placement.

Context:
- Pair raw values with historical comparisons and threshold indicators.

Labeling:
- Keep labels concise but unambiguous.
- Use abbreviations only when audience clearly understands them.

Iteration:
- Ask what users check most, ignore most, and what they still cannot answer.

