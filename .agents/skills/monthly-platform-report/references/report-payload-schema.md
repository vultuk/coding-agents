# Monthly Platform Report Payload Schema

Use this schema when preparing `report-payload.json` for `scripts/monthly_platform_report.py render`.

## Top-level keys

```json
{
  "group_name": "afx Markets Group",
  "month_label": "April 2026",
  "report_title": "Platform Report",
  "subtitle": "afx Hedge Fund | afx Markets | IGI Fund Managers",
  "confidential_label": "Confidential",
  "overview": "One concise executive summary paragraph.",
  "pages": []
}
```

## `pages`

`pages` is an ordered array of physical PDF pages.

- `pages[0]` is rendered as the cover page and also includes the first page's content sections.
- `pages[1:]` are rendered as interior pages with a repeated top header.

Each page object:

```json
{
  "title": "afx Markets",
  "sections": [
    {
      "heading": "Coverage & Exposure Reporting",
      "bullets": [
        "Bullet text 1.",
        "Bullet text 2."
      ]
    }
  ]
}
```

## Recommended report structure

### Page 1
- cover styling
- `overview`
- first content page, usually `afx Hedge Fund` or whichever product has the best opening section

### Interior pages
Suggested headings for `afx Markets` when the month is busy:
- `Coverage & Exposure Reporting`
- `Order Execution & Routing`
- `Slippage & Execution Analytics`
- `Copy-Trading & MAM`
- `FIX Protocol & Conformance`
- `Market Data & Pricing`
- `Observability & Monitoring`
- `Infrastructure & Reliability`
- `Conclusion`

Use only the headings that are actually supported by the changelog material.

## Authoring rules

- Keep bullets concrete and factual.
- Merge adjacent daily changelog items into one bullet when they describe the same theme.
- Avoid repeating daily changelog phrasing verbatim if a cleaner monthly summary is possible.
- Keep the conclusion to 1-3 bullets max.
