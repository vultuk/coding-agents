from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from textwrap import wrap
from typing import Iterable

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import LETTER
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.pdfgen import canvas
except ImportError:  # pragma: no cover - exercised through runtime checks
    colors = None
    LETTER = (612.0, 792.0)
    stringWidth = None
    canvas = None


PAGE_WIDTH, PAGE_HEIGHT = LETTER
LEFT_MARGIN = 64
RIGHT_MARGIN = 64
TOP_MARGIN = 48
BOTTOM_MARGIN = 44
CONTENT_WIDTH = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN
TOP_BANNER_HEIGHT = 290
FOOTER_Y = 34
HEADER_RULE_Y = PAGE_HEIGHT - 62
BODY_TOP_Y = PAGE_HEIGHT - 120
BODY_TEXT_COLOR = "#50556B"
TITLE_RED = "#C8102E"
LIGHT_RULE = "#E7E8EE"
HEADER_FOOTER_TEXT = "#8D93A6"
SUBHEADING_COLOR = "#1F2438"
ACCENT_LINE = "#F1B8B1"

DATE_HEADER_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s*$")


@dataclass
class ChangelogEntry:
    date: str
    summary: str

    def as_dict(self) -> dict[str, str]:
        return {"date": self.date, "summary": self.summary}


class ReportRenderError(RuntimeError):
    pass


def require_reportlab() -> None:
    if canvas is None or colors is None or stringWidth is None:
        raise ReportRenderError(
            "reportlab is required to render PDFs. Install it with `python -m pip install reportlab`."
        )


def month_label(year: int, month: int) -> str:
    return date(year, month, 1).strftime("%B %Y")


def parse_changelog_markdown(markdown: str) -> list[ChangelogEntry]:
    entries: list[ChangelogEntry] = []
    current_date: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_date, current_lines
        if current_date is None:
            return
        summary = " ".join(line.strip() for line in current_lines if line.strip()).strip()
        if summary:
            entries.append(ChangelogEntry(date=current_date, summary=summary))
        current_date = None
        current_lines = []

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        match = DATE_HEADER_RE.match(line)
        if match:
            flush()
            current_date = match.group(1)
            continue
        if current_date is not None:
            current_lines.append(line)

    flush()
    return entries


def collect_month_entries(
    changelog_paths: dict[str, str | Path],
    *,
    year: int,
    month: int,
    group_name: str = "afx Markets Group",
) -> dict[str, object]:
    prefix = f"{year:04d}-{month:02d}-"
    repositories: dict[str, list[dict[str, str]]] = {}

    for repo_name, raw_path in changelog_paths.items():
        path = Path(raw_path)
        markdown = path.read_text(encoding="utf-8")
        filtered = [entry.as_dict() for entry in parse_changelog_markdown(markdown) if entry.date.startswith(prefix)]
        filtered.sort(key=lambda item: item["date"], reverse=True)
        repositories[repo_name] = filtered

    return {
        "group_name": group_name,
        "month_label": month_label(year, month),
        "repositories": repositories,
    }


def render_pdf(payload: dict[str, object], output_path: str | Path) -> Path:
    require_reportlab()
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    pdf = canvas.Canvas(str(output), pagesize=LETTER)
    pages = list(payload.get("pages") or [])
    if not pages:
        raise ReportRenderError("payload.pages must contain at least one page definition")

    for index, page_payload in enumerate(pages, start=1):
        if index == 1:
            draw_cover_page(pdf, payload, page_payload, page_number=index)
        else:
            draw_interior_page(pdf, payload, page_payload, page_number=index)
        pdf.showPage()

    pdf.save()
    return output


def draw_cover_page(pdf: canvas.Canvas, payload: dict[str, object], page_payload: dict[str, object], *, page_number: int) -> None:
    draw_cover_banner(pdf, payload)
    y = PAGE_HEIGHT - TOP_BANNER_HEIGHT - 54
    y = draw_red_heading_with_rule(pdf, "Overview", y)
    overview_text = str(payload.get("overview") or "")
    ensure_vertical_space(
        y,
        required_height=estimate_paragraph_height(overview_text, width=CONTENT_WIDTH, font_name="Helvetica", font_size=11.5, leading=17) + 18 + 36,
        context="cover overview and first-page title",
    )
    y = draw_paragraph(
        pdf,
        overview_text,
        x=LEFT_MARGIN,
        y=y,
        width=CONTENT_WIDTH,
        font_name="Helvetica",
        font_size=11.5,
        leading=17,
        color=BODY_TEXT_COLOR,
    ) - 18
    y = draw_red_heading_with_rule(pdf, str(page_payload.get("title") or ""), y)
    draw_sections(pdf, page_payload, y)
    draw_footer(pdf, payload, page_number)


def draw_interior_page(pdf: canvas.Canvas, payload: dict[str, object], page_payload: dict[str, object], *, page_number: int) -> None:
    draw_interior_header(pdf, payload)
    y = BODY_TOP_Y
    title = str(page_payload.get("title") or "")
    pdf.setFillColor(colors.HexColor(TITLE_RED))
    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawString(LEFT_MARGIN, y, title)
    y -= 18
    draw_rule(pdf, y, colors.HexColor(LIGHT_RULE), thickness=1)
    y -= 22
    draw_sections(pdf, page_payload, y)
    draw_footer(pdf, payload, page_number)


def draw_sections(pdf: canvas.Canvas, page_payload: dict[str, object], start_y: float) -> float:
    y = start_y
    sections = list(page_payload.get("sections") or [])
    for section in sections:
        heading = str(section.get("heading") or "")
        bullets = [str(item) for item in section.get("bullets") or []]
        if heading:
            ensure_vertical_space(y, required_height=28, context=f"section heading '{heading}'")
            pdf.setFillColor(colors.HexColor(SUBHEADING_COLOR))
            pdf.setFont("Helvetica-Bold", 15)
            pdf.drawString(LEFT_MARGIN, y, heading)
            y -= 18
        for bullet in bullets:
            ensure_vertical_space(y, required_height=estimate_bullet_height(bullet), context=f"bullet under '{heading or page_payload.get('title', 'section')}'")
            y = draw_bullet(pdf, bullet, y)
            y -= 6
        y -= 10
    return y


def draw_cover_banner(pdf: canvas.Canvas, payload: dict[str, object]) -> None:
    banner_bottom = PAGE_HEIGHT - TOP_BANNER_HEIGHT
    pdf.setFillColor(colors.HexColor(TITLE_RED))
    pdf.rect(0, banner_bottom, PAGE_WIDTH, TOP_BANNER_HEIGHT, stroke=0, fill=1)

    date_y = banner_bottom + 120
    pdf.setFillColor(colors.HexColor("#F6C7C1"))
    pdf.setFont("Helvetica", 16)
    pdf.drawString(LEFT_MARGIN, date_y, str(payload.get("month_label") or ""))

    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 30)
    pdf.drawString(LEFT_MARGIN, date_y - 34, str(payload.get("report_title") or "Platform Report"))

    pdf.setStrokeColor(colors.HexColor(ACCENT_LINE))
    pdf.setLineWidth(2)
    pdf.line(LEFT_MARGIN, date_y - 48, LEFT_MARGIN + 180, date_y - 48)

    pdf.setFillColor(colors.HexColor("#F6C7C1"))
    pdf.setFont("Helvetica", 13)
    pdf.drawString(LEFT_MARGIN, date_y - 72, str(payload.get("subtitle") or ""))


def draw_interior_header(pdf: canvas.Canvas, payload: dict[str, object]) -> None:
    pdf.setFillColor(colors.HexColor(HEADER_FOOTER_TEXT))
    pdf.setFont("Helvetica", 10.5)
    pdf.drawString(LEFT_MARGIN, PAGE_HEIGHT - 38, str(payload.get("group_name") or ""))
    right_label = f"{payload.get('month_label', '')} {payload.get('report_title', 'Platform Report')}".strip()
    pdf.drawRightString(PAGE_WIDTH - RIGHT_MARGIN, PAGE_HEIGHT - 38, right_label)
    draw_rule(pdf, HEADER_RULE_Y, colors.HexColor(TITLE_RED), thickness=2)


def draw_footer(pdf: canvas.Canvas, payload: dict[str, object], page_number: int) -> None:
    draw_rule(pdf, FOOTER_Y + 16, colors.HexColor(LIGHT_RULE), thickness=1)
    pdf.setFillColor(colors.HexColor(HEADER_FOOTER_TEXT))
    pdf.setFont("Helvetica", 10.5)
    pdf.drawString(LEFT_MARGIN, FOOTER_Y, str(payload.get("confidential_label") or "Confidential"))
    pdf.drawRightString(PAGE_WIDTH - RIGHT_MARGIN, FOOTER_Y, f"Page {page_number}")


def draw_rule(pdf: canvas.Canvas, y: float, color: colors.Color, *, thickness: float) -> None:
    pdf.setStrokeColor(color)
    pdf.setLineWidth(thickness)
    pdf.line(LEFT_MARGIN, y, PAGE_WIDTH - RIGHT_MARGIN, y)


def ensure_vertical_space(y: float, *, required_height: float, context: str) -> None:
    minimum_y = FOOTER_Y + 24
    if y - required_height < minimum_y:
        raise ReportRenderError(
            f"Not enough vertical space to render {context}; add pagination or reduce the content for this page."
        )


def estimate_bullet_height(text: str) -> float:
    lines = wrap_text(text, width=CONTENT_WIDTH - 18, font_name="Helvetica", font_size=11.5)
    return ((len(lines) - 1) * 15) + 15


def estimate_paragraph_height(text: str, *, width: float, font_name: str, font_size: float, leading: float) -> float:
    lines = wrap_text(text, width=width, font_name=font_name, font_size=font_size)
    return len(lines) * leading


def draw_red_heading_with_rule(pdf: canvas.Canvas, heading: str, y: float) -> float:
    pdf.setFillColor(colors.HexColor(TITLE_RED))
    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawString(LEFT_MARGIN, y, heading)
    y -= 14
    draw_rule(pdf, y, colors.HexColor(LIGHT_RULE), thickness=1)
    return y - 22


def draw_bullet(pdf: canvas.Canvas, text: str, y: float) -> float:
    bullet_x = LEFT_MARGIN + 4
    text_x = LEFT_MARGIN + 18
    width = CONTENT_WIDTH - 18
    lines = wrap_text(text, width=width, font_name="Helvetica", font_size=11.5)
    pdf.setFillColor(colors.HexColor(BODY_TEXT_COLOR))
    pdf.setFont("Helvetica", 11.5)
    pdf.drawString(bullet_x, y, "•")
    for index, line in enumerate(lines):
        pdf.drawString(text_x, y - (index * 15), line)
    return y - ((len(lines) - 1) * 15) - 15


def draw_paragraph(
    pdf: canvas.Canvas,
    text: str,
    *,
    x: float,
    y: float,
    width: float,
    font_name: str,
    font_size: float,
    leading: float,
    color: str,
) -> float:
    lines = wrap_text(text, width=width, font_name=font_name, font_size=font_size)
    pdf.setFillColor(colors.HexColor(color))
    pdf.setFont(font_name, font_size)
    for index, line in enumerate(lines):
        pdf.drawString(x, y - (index * leading), line)
    return y - (len(lines) * leading)


def wrap_text(text: str, *, width: float, font_name: str, font_size: float) -> list[str]:
    require_reportlab()
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    if stringWidth(current, font_name, font_size) > width:
        raise ReportRenderError(
            "Encountered an unbreakable token that exceeds the available line width; shorten it or insert break opportunities before rendering."
        )
    for word in words[1:]:
        if stringWidth(word, font_name, font_size) > width:
            raise ReportRenderError(
                "Encountered an unbreakable token that exceeds the available line width; shorten it or insert break opportunities before rendering."
            )
        candidate = f"{current} {word}"
        if stringWidth(candidate, font_name, font_size) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def parse_repo_path(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("repo arguments must be in NAME=/path/to/Changelog.md form")
    name, path = value.split("=", 1)
    name = name.strip()
    path = path.strip()
    if not name or not path:
        raise argparse.ArgumentTypeError("repo arguments must include both a name and a path")
    return name, path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build monthly platform report inputs and PDFs.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract_parser = subparsers.add_parser("extract-month", help="Extract month entries from repo changelogs.")
    extract_parser.add_argument("--year", type=int, required=True)
    extract_parser.add_argument("--month", type=int, required=True)
    extract_parser.add_argument(
        "--repo",
        dest="repos",
        action="append",
        type=parse_repo_path,
        required=True,
        help="Repeatable NAME=/path/to/Changelog.md input",
    )
    extract_parser.add_argument("--group-name", default="afx Markets Group")
    extract_parser.add_argument("--output-json", type=Path)

    render_parser = subparsers.add_parser("render", help="Render a PDF from a prepared JSON payload.")
    render_parser.add_argument("--input-json", type=Path, required=True)
    render_parser.add_argument("--output-pdf", type=Path, required=True)

    return parser


def handle_extract_month(args: argparse.Namespace) -> int:
    report_inputs = collect_month_entries(
        dict(args.repos),
        year=args.year,
        month=args.month,
        group_name=args.group_name,
    )
    text = json.dumps(report_inputs, indent=2)
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


def handle_render(args: argparse.Namespace) -> int:
    payload = json.loads(args.input_json.read_text(encoding="utf-8"))
    render_pdf(payload, args.output_pdf)
    print(str(args.output_pdf))
    return 0


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.command == "extract-month":
        return handle_extract_month(args)
    if args.command == "render":
        return handle_render(args)
    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
