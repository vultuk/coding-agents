from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import pymupdf


MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "monthly_platform_report.py"
)
SPEC = importlib.util.spec_from_file_location("monthly_platform_report", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load monthly_platform_report module for tests.")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


AFX_MARKETS_CHANGELOG = """# Changelog
## 2026-04-17
FIX infrastructure was renamed from fix-server to fix-provider, and the logon flow now records source IP addresses for connection attempts.

## 2026-04-16
Pricing and market data support landed for the FIX server, along with MT5 account mapping, symbol entitlements, and end-to-end session boundary coverage.

## 2026-03-31
Old month entry that should be filtered out.
"""

AFX_HEDGE_FUND_CHANGELOG = """# Changelog
## 2026-04-15
MT5 proxy connectivity now consistently follows environment-based settings, making deployments more predictable.

## 2026-04-08
Coin API failures now return consistent server-error messages.
"""

IGI_CHANGELOG = """# Changelog
## 2026-04-12
Withdrawal processing windows are now driven by configuration instead of hard-coded client behavior.
"""


class MonthlyPlatformReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.temp_path = Path(self.temp_dir.name)

    def write_changelog(self, name: str, content: str) -> Path:
        path = self.temp_path / f"{name}.md"
        path.write_text(content, encoding="utf-8")
        return path

    def test_collect_month_entries_filters_and_sorts_by_date(self) -> None:
        changelog_paths = {
            "afx-markets": self.write_changelog("afx-markets", AFX_MARKETS_CHANGELOG),
            "afx-hedge-fund": self.write_changelog("afx-hedge-fund", AFX_HEDGE_FUND_CHANGELOG),
            "igi-fund-managers": self.write_changelog("igi-fund-managers", IGI_CHANGELOG),
        }

        report_inputs = MODULE.collect_month_entries(changelog_paths, year=2026, month=4)

        self.assertEqual(report_inputs["month_label"], "April 2026")
        self.assertEqual(
            [entry["date"] for entry in report_inputs["repositories"]["afx-markets"]],
            ["2026-04-17", "2026-04-16"],
        )
        self.assertEqual(
            report_inputs["repositories"]["igi-fund-managers"][0]["summary"],
            "Withdrawal processing windows are now driven by configuration instead of hard-coded client behavior.",
        )

    def test_render_pdf_writes_expected_titles_sections_and_footer_text(self) -> None:
        output_path = self.temp_path / "platform-report.pdf"
        payload = {
            "group_name": "afx Markets Group",
            "month_label": "April 2026",
            "report_title": "Platform Report",
            "subtitle": "afx Hedge Fund | afx Markets | IGI Fund Managers",
            "confidential_label": "Confidential",
            "overview": (
                "April month-to-date concentrated on order execution reliability, coverage reporting, "
                "and operational tooling across the platforms."
            ),
            "pages": [
                {
                    "title": "afx Hedge Fund",
                    "sections": [
                        {
                            "heading": "Automation & Reliability",
                            "bullets": [
                                "Coin API failures now return clear server-error messages.",
                                "MT5 proxy connectivity now follows environment-based settings more consistently.",
                            ],
                        }
                    ],
                },
                {
                    "title": "afx Markets",
                    "sections": [
                        {
                            "heading": "FIX Protocol & Conformance",
                            "bullets": [
                                "FIX infrastructure was renamed from fix-server to fix-provider.",
                                "Pricing and market data support landed alongside MT5 mappings and symbol entitlements.",
                            ],
                        },
                        {
                            "heading": "Conclusion",
                            "bullets": [
                                "April month-to-date improved execution trust, reporting accuracy, and operational response times.",
                            ],
                        },
                    ],
                },
            ],
        }

        MODULE.render_pdf(payload, output_path)

        self.assertTrue(output_path.exists())
        self.assertGreater(output_path.stat().st_size, 0)

        doc = pymupdf.open(output_path)
        self.assertEqual(doc.page_count, 2)
        page_1_text = doc.load_page(0).get_text("text")
        page_2_text = doc.load_page(1).get_text("text")
        self.assertIn("April 2026", page_1_text)
        self.assertIn("Platform Report", page_1_text)
        self.assertIn("Automation & Reliability", page_1_text)
        self.assertIn("Confidential", page_1_text)
        self.assertIn("afx Markets Group", page_2_text)
        self.assertIn("FIX Protocol & Conformance", page_2_text)
        self.assertIn("Conclusion", page_2_text)
        self.assertIn("Page 2", page_2_text)

    def test_cli_render_command_reads_json_and_creates_pdf(self) -> None:
        payload_path = self.temp_path / "payload.json"
        output_path = self.temp_path / "cli-platform-report.pdf"
        payload_path.write_text(
            json.dumps(
                {
                    "group_name": "afx Markets Group",
                    "month_label": "April 2026",
                    "report_title": "Platform Report",
                    "subtitle": "afx Hedge Fund | afx Markets | IGI Fund Managers",
                    "confidential_label": "Confidential",
                    "overview": "Short overview.",
                    "pages": [
                        {
                            "title": "afx Hedge Fund",
                            "sections": [
                                {
                                    "heading": "Automation & Reliability",
                                    "bullets": ["Example bullet."],
                                }
                            ],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        exit_code = MODULE.main(
            [
                "render",
                "--input-json",
                str(payload_path),
                "--output-pdf",
                str(output_path),
            ]
        )

        self.assertEqual(exit_code, 0)
        self.assertTrue(output_path.exists())

    def test_extract_month_cli_creates_parent_directories_for_output_json(self) -> None:
        changelog_path = self.write_changelog("afx-markets", AFX_MARKETS_CHANGELOG)
        output_path = self.temp_path / "nested" / "month-input.json"

        exit_code = MODULE.main(
            [
                "extract-month",
                "--year",
                "2026",
                "--month",
                "4",
                "--repo",
                f"afx-markets={changelog_path}",
                "--output-json",
                str(output_path),
            ]
        )

        self.assertEqual(exit_code, 0)
        self.assertTrue(output_path.exists())
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["month_label"], "April 2026")

    def test_render_pdf_raises_when_bullet_contains_unbreakable_long_token(self) -> None:
        output_path = self.temp_path / "long-token-platform-report.pdf"
        payload = {
            "group_name": "afx Markets Group",
            "month_label": "April 2026",
            "report_title": "Platform Report",
            "subtitle": "afx Hedge Fund | afx Markets | IGI Fund Managers",
            "confidential_label": "Confidential",
            "overview": "Short overview.",
            "pages": [
                {
                    "title": "afx Markets",
                    "sections": [
                        {
                            "heading": "Diagnostics",
                            "bullets": ["X" * 300],
                        }
                    ],
                }
            ],
        }

        with self.assertRaises(MODULE.ReportRenderError):
            MODULE.render_pdf(payload, output_path)

    def test_render_pdf_raises_when_cover_overview_would_overflow(self) -> None:
        output_path = self.temp_path / "overflow-overview-platform-report.pdf"
        payload = {
            "group_name": "afx Markets Group",
            "month_label": "April 2026",
            "report_title": "Platform Report",
            "subtitle": "afx Hedge Fund | afx Markets | IGI Fund Managers",
            "confidential_label": "Confidential",
            "overview": "This overview sentence is intentionally repeated to exceed the available cover-page space. " * 120,
            "pages": [
                {
                    "title": "afx Hedge Fund",
                    "sections": [],
                }
            ],
        }

        with self.assertRaises(MODULE.ReportRenderError):
            MODULE.render_pdf(payload, output_path)

    def test_render_pdf_raises_when_page_content_would_overflow(self) -> None:
        output_path = self.temp_path / "overflow-platform-report.pdf"
        payload = {
            "group_name": "afx Markets Group",
            "month_label": "April 2026",
            "report_title": "Platform Report",
            "subtitle": "afx Hedge Fund | afx Markets | IGI Fund Managers",
            "confidential_label": "Confidential",
            "overview": "Short overview.",
            "pages": [
                {
                    "title": "afx Markets",
                    "sections": [
                        {
                            "heading": f"Section {idx}",
                            "bullets": [
                                "This is a deliberately long bullet meant to consume a lot of vertical space in the renderer. "
                                * 3
                                for _ in range(6)
                            ],
                        }
                        for idx in range(1, 10)
                    ],
                }
            ],
        }

        with self.assertRaises(MODULE.ReportRenderError):
            MODULE.render_pdf(payload, output_path)


if __name__ == "__main__":
    unittest.main()
