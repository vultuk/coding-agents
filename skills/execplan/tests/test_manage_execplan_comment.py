from __future__ import annotations

import argparse
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "manage_execplan_comment.py"
)
SPEC = importlib.util.spec_from_file_location("manage_execplan_comment", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load manage_execplan_comment module for tests.")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ManageExecplanCommentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.plan_path = Path(self.temp_dir.name) / "plan.md"

    def test_normalize_uses_terse_placeholders(self) -> None:
        self.plan_path.write_text("", encoding="utf-8")
        args = argparse.Namespace(
            input=str(self.plan_path),
            output=None,
            title="Implement issue #123",
            meta_file=None,
            meta_json='{"issue": 123, "repo": "acme/widgets"}',
        )

        MODULE.normalize_command(args)

        body = self.plan_path.read_text(encoding="utf-8")
        self.assertIn("## Concrete Steps\n\nPending.", body)
        self.assertIn("## Surprises & Discoveries\n\n- None yet.", body)
        self.assertNotIn("State the exact commands to run, where to run them", body)
        self.assertNotIn("Describe the planned sequence of changes in prose", body)

    def test_normalize_hides_metadata_inside_single_html_comment(self) -> None:
        self.plan_path.write_text("<!-- execplan:managed -->\n# Implement issue #123\n", encoding="utf-8")
        args = argparse.Namespace(
            input=str(self.plan_path),
            output=None,
            title="Implement issue #123",
            meta_file=None,
            meta_json='{"issue": 123, "repo": "acme/widgets", "commentId": 42}',
        )

        MODULE.normalize_command(args)

        body = self.plan_path.read_text(encoding="utf-8")
        self.assertIn('<!-- execplan:meta\n', body)
        self.assertIn('\n-->\n', body)
        self.assertNotIn('<!-- execplan:meta:start -->', body)
        self.assertNotIn('<!-- execplan:meta:end -->', body)
        self.assertNotIn('  "commentId": 42,', body)

        _, parsed = MODULE.strip_metadata_block(body)
        self.assertEqual(parsed["commentId"], 42)
        self.assertEqual(parsed["repo"], "acme/widgets")

    def test_normalize_migrates_legacy_visible_metadata_block(self) -> None:
        self.plan_path.write_text(
            "\n".join(
                [
                    "<!-- execplan:managed -->",
                    "# Implement issue #123",
                    "",
                    "<!-- execplan:meta:start -->",
                    '{"issue": 123, "repo": "acme/widgets", "commentId": 42}',
                    "<!-- execplan:meta:end -->",
                    "",
                    "## Context and Orientation",
                    "Existing prose.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        args = argparse.Namespace(
            input=str(self.plan_path),
            output=None,
            title="Implement issue #123",
            meta_file=None,
            meta_json='{"planRevision": 2}',
        )

        MODULE.normalize_command(args)

        body = self.plan_path.read_text(encoding="utf-8")
        self.assertIn('<!-- execplan:meta\n', body)
        self.assertNotIn('<!-- execplan:meta:start -->', body)
        self.assertNotIn('<!-- execplan:meta:end -->', body)
        self.assertNotIn('  "commentId": 42,', body)
        self.assertNotIn('  "planRevision": 2,', body)
        self.assertIn('Existing prose.', body)

        _, parsed = MODULE.strip_metadata_block(body)
        self.assertEqual(parsed["commentId"], 42)
        self.assertEqual(parsed["planRevision"], 2)

    def test_normalize_hides_metadata_with_html_comment_terminator_in_value(self) -> None:
        self.plan_path.write_text("<!-- execplan:managed -->\n# Implement issue #123\n", encoding="utf-8")
        args = argparse.Namespace(
            input=str(self.plan_path),
            output=None,
            title="Implement issue #123",
            meta_file=None,
            meta_json='{"issue": 123, "validation": {"summary": "value with --> terminator"}}',
        )

        MODULE.normalize_command(args)

        body = self.plan_path.read_text(encoding="utf-8")
        self.assertNotIn("value with --> terminator", body)

        _, parsed = MODULE.strip_metadata_block(body)
        self.assertEqual(parsed["validation"]["summary"], "value with --> terminator")

    def test_record_slice_marks_progress_and_adds_evidence(self) -> None:
        self.plan_path.write_text("<!-- execplan:managed -->\n# Implement issue #123\n", encoding="utf-8")

        args = argparse.Namespace(
            input=str(self.plan_path),
            output=None,
            title="Implement issue #123",
            meta_file=None,
            meta_json='{"issue": 123}',
            slice_id="EP-002",
            summary="Add regression coverage for disabled providers",
            state="done",
            time="2026-04-02T12:00:00Z",
            kind="validation",
            action="python3 -m unittest skills.execplan.tests",
            cwd="<repo-root>",
            result="Passed",
            proof="2 tests passed",
        )

        MODULE.record_slice_command(args)

        body = self.plan_path.read_text(encoding="utf-8")
        self.assertIn(
            "- [x] EP-002 (2026-04-02T12:00:00Z) Add regression coverage for disabled providers",
            body,
        )
        self.assertIn("- slice: EP-002", body)
        self.assertIn("  cwd: <repo-root>", body)
        self.assertIn("  proof: 2 tests passed", body)

    def test_lint_rejects_machine_local_paths_in_visible_content(self) -> None:
        self.plan_path.write_text(
            "\n".join(
                [
                    "<!-- execplan:managed -->",
                    "# Implement issue #123",
                    "## Concrete Steps",
                    "From /Users/alice/.codex/worktrees/56c1/project, update src/app.ts.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        args = argparse.Namespace(input=str(self.plan_path))
        with self.assertRaises(SystemExit):
            MODULE.lint_command(args)

    def test_lint_ignores_repo_relative_content(self) -> None:
        self.plan_path.write_text(
            "\n".join(
                [
                    "<!-- execplan:managed -->",
                    "# Implement issue #123",
                    "## Concrete Steps",
                    "From <repo-root>, update apps/portal/src/view.tsx and run pnpm test --filter portal.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        args = argparse.Namespace(input=str(self.plan_path))
        MODULE.lint_command(args)


if __name__ == "__main__":
    unittest.main()
