---
name: monthly-platform-report
description: Build a branded monthly Platform Report PDF from the afx-markets, afx-hedge-fund, and igi-fund-managers wiki changelogs by extracting month-specific entries, synthesizing report copy, and rendering a PDF that matches the established report style.
---

# Monthly Platform Report

Generate a monthly Platform Report PDF from the three product changelogs:
- `nummus-software/afx-markets`
- `nummus-software/afx-hedge-fund`
- `nummus-software/igi-fund-managers`

The output should closely match the established branded PDF style:
- crimson cover banner on page 1
- `Month YYYY` + `Platform Report` title block
- subtitle naming the platforms
- `Overview` on page 1
- product pages with bold dark section headings and bullet lists
- footer with `Confidential` and page numbers

## Default Inputs

- Default repositories: the three repos above.
- Default timezone: `UTC`.
- Default month: current UTC month unless the user specifies another one.
- Default output filename: `YYYY-MM-platform-report.pdf`.
- Default group name: `afx Markets Group`.
- Default subtitle: `afx Hedge Fund | afx Markets | IGI Fund Managers`.

## Required Tools

- `terminal` for `gh`, `git`, and Python execution.
- `read_file` for inspecting generated JSON or markdown when needed.
- `write_file` for report payloads or notes when useful.
- The helper script in this skill:
  - `scripts/monthly_platform_report.py`

### Important linked-file note

The helper script is a **linked skill file**, not something that will necessarily exist under the current shell working directory. Load it with:

```python
skill_view(name="monthly-platform-report", file_path="scripts/monthly_platform_report.py")
```

Then, if needed for execution, write that content into a runnable path in the active workspace before calling it. Do **not** assume `python skills/monthly-platform-report/scripts/monthly_platform_report.py ...` will work unless you have already confirmed that path exists in the current filesystem context.

## Preflight

1. Set GitHub auth path when working in work-dev:
   ```bash
   export GH_CONFIG_DIR=/home/ec2-user/.config/gh
   ```
2. Verify GitHub access:
   ```bash
   gh auth status
   ```
3. Ensure PDF tooling is available before doing synthesis work:
   ```bash
   python -m pip install reportlab pymupdf
   ```
   - `reportlab` is required for rendering the PDF.
   - `pymupdf` is useful for inspecting a sample report, validating generated output, and extracting page text during QA.
4. Clone the three wiki repos into a temporary directory:
   ```bash
   gh repo clone nummus-software/afx-markets.wiki "$WORKDIR/afx-markets-wiki"
   gh repo clone nummus-software/afx-hedge-fund.wiki "$WORKDIR/afx-hedge-fund-wiki"
   gh repo clone nummus-software/igi-fund-managers.wiki "$WORKDIR/igi-fund-managers-wiki"
   ```
4. Confirm each wiki contains `Changelog.md`.

## Step 1: Extract The Month's Changelog Entries

Use the helper script to build a machine-readable input bundle:

```bash
python skills/monthly-platform-report/scripts/monthly_platform_report.py extract-month \
  --year 2026 \
  --month 4 \
  --repo afx-markets="$WORKDIR/afx-markets-wiki/Changelog.md" \
  --repo afx-hedge-fund="$WORKDIR/afx-hedge-fund-wiki/Changelog.md" \
  --repo igi-fund-managers="$WORKDIR/igi-fund-managers-wiki/Changelog.md" \
  --output-json "$WORKDIR/month-input.json"
```

This produces JSON shaped like:

```json
{
  "group_name": "afx Markets Group",
  "month_label": "April 2026",
  "repositories": {
    "afx-markets": [{"date": "2026-04-17", "summary": "..."}],
    "afx-hedge-fund": [{"date": "2026-04-15", "summary": "..."}],
    "igi-fund-managers": [{"date": "2026-04-12", "summary": "..."}]
  }
}
```

## Step 2: Synthesize The Report Copy

From the extracted month entries, create a structured report payload JSON for rendering.

Use the source changelog language as the basis, but rewrite it into clean monthly-report prose.

### Writing rules

- Keep it executive-readable and concrete.
- Do not repeat changelog dates in the PDF body.
- Prefer named workflows/systems over vague categories.
- Avoid filler like:
  - "focused on"
  - "new capabilities"
  - "more polished and dependable experience"
- The `overview` should be one concise paragraph.
- Each section should contain bullet points that consolidate multiple daily changelog items where sensible.
- Preserve factual boundaries: do not invent features not present in the changelogs.
- If one source repo has no entries for the requested month, say so explicitly in the report instead of fabricating summary copy.
- If the monthly changelog input is itself low-quality or generic, rewrite it into the most concrete truthful summary possible, but keep the report honest about the thinness of the underlying source material.

### Recommended page structure

Use a payload shaped like:

```json
{
  "group_name": "afx Markets Group",
  "month_label": "April 2026",
  "report_title": "Platform Report",
  "subtitle": "afx Hedge Fund | afx Markets | IGI Fund Managers",
  "confidential_label": "Confidential",
  "overview": "...",
  "pages": [
    {
      "title": "afx Hedge Fund",
      "sections": [
        {"heading": "Automation & Reliability", "bullets": ["...", "..."]}
      ]
    },
    {
      "title": "afx Markets",
      "sections": [
        {"heading": "Coverage & Exposure Reporting", "bullets": ["...", "..."]},
        {"heading": "Order Execution & Routing", "bullets": ["...", "..."]}
      ]
    },
    {
      "title": "afx Markets",
      "sections": [
        {"heading": "FIX Protocol & Conformance", "bullets": ["...", "..."]},
        {"heading": "Infrastructure & Reliability", "bullets": ["...", "..."]},
        {"heading": "Conclusion", "bullets": ["..."]}
      ]
    }
  ]
}
```

### Section conventions

- Page 1 doubles as cover + overview + first product page.
- Use `afx Hedge Fund` as the first page title when that repo has meaningful monthly content.
- Use one or more `afx Markets` pages for the bulk of the report.
- Include `igi-fund-managers` either as its own page or as a dedicated section when the month's content is light.
- End the last page with a `Conclusion` section.

## Step 3: Render The PDF

Save the synthesized payload to JSON, then render it:

```bash
python skills/monthly-platform-report/scripts/monthly_platform_report.py render \
  --input-json "$WORKDIR/report-payload.json" \
  --output-pdf "$WORKDIR/2026-04-platform-report.pdf"
```

The renderer handles:
- the crimson page-1 banner
- interior page headers
- section rules
- bullets
- footer text and page numbering
- fail-fast validation for oversized page content, including cover-overview overflow, section/bullet vertical overflow, and unbreakable tokens that exceed line width

Operational notes:
- `extract-month --output-json` creates parent directories automatically.
- `render` is intentionally conservative: if synthesized content cannot fit safely on a page, it raises `ReportRenderError` instead of silently clipping or overlapping content.

## Verification Checklist

Before finishing:

1. Open or inspect the PDF text to confirm:
   - correct month label
   - title `Platform Report`
   - overview present
   - expected page titles and section headings present
   - footer text includes `Confidential`
2. Confirm the PDF filename matches the requested month.
3. Confirm the copy only reflects that month's changelog material.
4. If the user asked for delivery, send the generated PDF file.

## Example Validation Commands

```bash
python -m unittest skills/monthly-platform-report/tests/test_monthly_platform_report.py -v
python skills/monthly-platform-report/scripts/monthly_platform_report.py --help
```

## Output Contract

Return:
- the month covered
- the PDF output path
- the repos used as sources
- any notable synthesis choices, such as combining light IGI content into a shared page

## Cleanup

- Remove temporary wiki clones when done.
- Keep the final PDF only if the user asked for it or if it is needed for delivery.
