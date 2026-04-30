from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "pr_feedback_loop.py"
)
SPEC = importlib.util.spec_from_file_location("pr_feedback_loop", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load pr_feedback_loop module for tests.")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def make_context(state: str = "OPEN", head_sha: str = "sha-1") -> dict[str, str | int]:
    return {
        "repo": "acme/widgets",
        "owner": "acme",
        "name": "widgets",
        "number": 42,
        "url": "https://github.com/acme/widgets/pull/42",
        "title": "Fix workflow loop",
        "state": state,
        "head_sha": head_sha,
        "head_ref": "fix/workflow",
        "base_ref": "main",
    }


def make_review_item(key: str = "review:10", body_hash: str = "hash-a") -> dict[str, str]:
    return {
        "key": key,
        "type": "review",
        "review_id": key.split(":")[-1],
        "body_hash": body_hash,
        "author": "reviewer",
        "summary": "Please change this",
        "body": "Please change this",
        "updated_at": "2026-03-26T10:00:00Z",
        "url": "https://github.com/acme/widgets/pull/42#pullrequestreview-10",
    }


def make_thread_item(body_hash: str = "thread-a") -> dict[str, object]:
    return {
        "key": "thread:77",
        "type": "thread",
        "thread_id": "77",
        "comment_ids": ["7001"],
        "body_hash": body_hash,
        "author": "reviewer",
        "summary": "Inline feedback",
        "body": "Inline feedback",
        "updated_at": "2026-03-26T10:05:00Z",
        "url": "https://github.com/acme/widgets/pull/42#discussion_r7001",
    }


def make_ci_item(head_sha: str, body_hash: str = "ci-a") -> dict[str, str]:
    return {
        "key": f"ci:test-suite:{head_sha}",
        "type": "ci_failure",
        "failure_class": "test-suite",
        "head_sha": head_sha,
        "check_name": "Test Suite",
        "body_hash": body_hash,
        "summary": "Test Suite (failure)",
        "state": "completed",
        "conclusion": "failure",
        "updated_at": "2026-03-26T10:10:00Z",
        "url": "https://github.com/acme/widgets/actions/runs/1",
    }


class FakeProvider:
    def __init__(self, iterations, *, context=None, login="agent"):
        self.iterations = list(iterations)
        self.context = context or make_context()
        self.login = login

    def resolve_context(self):
        return dict(self.context)

    def resolve_self_login(self):
        return self.login

    def fetch_iteration(self, context, self_login):
        entry = self.iterations.pop(0)
        if isinstance(entry, Exception):
            raise entry
        current_context = dict(self.context)
        current_context.update(entry.get("context") or {})
        return MODULE.IterationData(
            context=current_context,
            items=list(entry.get("items") or []),
            failed_checks=list(entry.get("failed_checks") or []),
        )


class PrFeedbackLoopTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.state_file = Path(self.temp_dir.name) / "state.json"

    def load_state(self):
        return json.loads(self.state_file.read_text(encoding="utf-8"))

    def test_new_review_is_detected_once(self):
        provider = FakeProvider(
            [
                {"items": [make_review_item()]},
                {"items": [make_review_item()]},
            ]
        )

        result1, _state1 = MODULE.run_monitor(
            provider,
            mode="once",
            poll_seconds=300,
            state_file=self.state_file,
            mark_handled=[],
            blocked_specs=[],
            increment_retry=[],
            clear_retry=[],
            last_action_summary=None,
            jitter_seconds=0,
        )
        self.assertEqual(result1["status"], "actionable")
        self.assertEqual([item["key"] for item in result1["new_items"]], ["review:10"])

        provider = FakeProvider([{"items": [make_review_item()]}])
        result2, _state2 = MODULE.run_monitor(
            provider,
            mode="once",
            poll_seconds=300,
            state_file=self.state_file,
            mark_handled=["review:10"],
            blocked_specs=[],
            increment_retry=[],
            clear_retry=[],
            last_action_summary="Replied on the review thread",
            jitter_seconds=0,
        )
        self.assertEqual(result2["status"], "idle")
        self.assertEqual(result2["new_items"], [])
        state = self.load_state()
        self.assertEqual(state["handled_body_hashes"]["review:10"], "hash-a")

    def test_edited_thread_body_is_treated_as_updated_work(self):
        provider = FakeProvider([{"items": [make_thread_item(body_hash="thread-a")]}])
        MODULE.run_monitor(
            provider,
            mode="once",
            poll_seconds=300,
            state_file=self.state_file,
            mark_handled=[],
            blocked_specs=[],
            increment_retry=[],
            clear_retry=[],
            last_action_summary=None,
            jitter_seconds=0,
        )

        provider = FakeProvider([{"items": [make_thread_item(body_hash="thread-a")]}])
        MODULE.run_monitor(
            provider,
            mode="once",
            poll_seconds=300,
            state_file=self.state_file,
            mark_handled=["thread:77"],
            blocked_specs=[],
            increment_retry=[],
            clear_retry=[],
            last_action_summary="Addressed inline feedback",
            jitter_seconds=0,
        )

        provider = FakeProvider([{"items": [make_thread_item(body_hash="thread-b")]}])
        result, _state = MODULE.run_monitor(
            provider,
            mode="once",
            poll_seconds=300,
            state_file=self.state_file,
            mark_handled=[],
            blocked_specs=[],
            increment_retry=[],
            clear_retry=[],
            last_action_summary=None,
            jitter_seconds=0,
        )

        self.assertEqual(result["status"], "actionable")
        self.assertEqual(result["new_items"], [])
        self.assertEqual([item["key"] for item in result["updated_items"]], ["thread:77"])

    def test_watch_mode_keeps_polling_across_idle_iterations(self):
        sleep_calls = []
        provider = FakeProvider(
            [
                {"items": []},
                {"items": [make_review_item(key="review:11", body_hash="hash-b")]},
            ]
        )

        result, _state = MODULE.run_monitor(
            provider,
            mode="watch",
            poll_seconds=300,
            state_file=self.state_file,
            mark_handled=[],
            blocked_specs=[],
            increment_retry=[],
            clear_retry=[],
            last_action_summary=None,
            jitter_seconds=0,
            sleep_fn=lambda seconds: sleep_calls.append(seconds),
        )

        self.assertEqual(result["status"], "actionable")
        self.assertEqual(result["iteration"], 2)
        self.assertEqual(sleep_calls, [300])

    def test_same_ci_failure_same_sha_is_deduped_but_new_sha_reopens(self):
        first_ci = make_ci_item("sha-1", body_hash="ci-sha1")
        provider = FakeProvider([{"items": [first_ci], "failed_checks": [first_ci]}])
        result1, _state1 = MODULE.run_monitor(
            provider,
            mode="once",
            poll_seconds=300,
            state_file=self.state_file,
            mark_handled=[],
            blocked_specs=[],
            increment_retry=[],
            clear_retry=[],
            last_action_summary=None,
            jitter_seconds=0,
        )
        self.assertEqual(result1["status"], "actionable")

        provider = FakeProvider([{"items": [first_ci], "failed_checks": [first_ci]}], context=make_context(head_sha="sha-1"))
        result2, _state2 = MODULE.run_monitor(
            provider,
            mode="once",
            poll_seconds=300,
            state_file=self.state_file,
            mark_handled=[first_ci["key"]],
            blocked_specs=[],
            increment_retry=[],
            clear_retry=[],
            last_action_summary="Retried flaky CI job",
            jitter_seconds=0,
        )
        self.assertEqual(result2["status"], "idle")

        second_ci = make_ci_item("sha-2", body_hash="ci-sha2")
        provider = FakeProvider([{"items": [second_ci], "failed_checks": [second_ci]}], context=make_context(head_sha="sha-2"))
        result3, _state3 = MODULE.run_monitor(
            provider,
            mode="once",
            poll_seconds=300,
            state_file=self.state_file,
            mark_handled=[],
            blocked_specs=[],
            increment_retry=[],
            clear_retry=[],
            last_action_summary=None,
            jitter_seconds=0,
        )
        self.assertEqual(result3["status"], "actionable")
        self.assertEqual([item["key"] for item in result3["new_items"]], [second_ci["key"]])

    def test_gh_checks_bucket_schema_is_normalised(self):
        passing = MODULE.normalise_check_item(
            {
                "name": "Quality Lint",
                "state": "SUCCESS",
                "bucket": "pass",
                "link": "https://github.com/acme/widgets/actions/runs/1",
            },
            "sha-1",
        )
        self.assertIsNone(passing)

        failing = MODULE.normalise_check_item(
            {
                "name": "Quality Test",
                "state": "FAILURE",
                "bucket": "fail",
                "link": "https://github.com/acme/widgets/actions/runs/2",
            },
            "sha-1",
        )
        self.assertIsNotNone(failing)
        self.assertEqual(failing["key"], "ci:quality-test:sha-1")
        self.assertEqual(failing["conclusion"], "fail")

    def test_gh_checks_legacy_conclusion_schema_is_normalised(self):
        failing = MODULE.normalise_check_item(
            {
                "name": "Legacy Test",
                "state": "COMPLETED",
                "conclusion": "failure",
                "link": "https://github.com/acme/widgets/actions/runs/3",
            },
            "sha-1",
        )

        self.assertIsNotNone(failing)
        self.assertEqual(failing["key"], "ci:legacy-test:sha-1")
        self.assertEqual(failing["conclusion"], "failure")

    def test_gh_checks_cancel_bucket_is_actionable(self):
        cancelled = MODULE.normalise_check_item(
            {
                "name": "Cancelled Test",
                "state": "COMPLETED",
                "bucket": "cancel",
                "link": "https://github.com/acme/widgets/actions/runs/4",
            },
            "sha-1",
        )

        self.assertIsNotNone(cancelled)
        self.assertEqual(cancelled["key"], "ci:cancelled-test:sha-1")
        self.assertEqual(cancelled["conclusion"], "cancel")

    def test_gh_checks_command_requests_legacy_and_bucket_fields(self):
        self.assertEqual(
            MODULE.GH_CHECK_JSON_FIELDS,
            "name,state,conclusion,bucket,link",
        )

    def test_retry_counters_persist_across_runs(self):
        provider = FakeProvider([{"items": [make_review_item()]}])
        MODULE.run_monitor(
            provider,
            mode="once",
            poll_seconds=300,
            state_file=self.state_file,
            mark_handled=[],
            blocked_specs=[],
            increment_retry=["ci:test-suite:sha-1"],
            clear_retry=[],
            last_action_summary="Retrying CI after timeout",
            jitter_seconds=0,
        )
        state = self.load_state()
        self.assertEqual(state["retry_counters"]["ci:test-suite:sha-1"]["count"], 1)

        provider = FakeProvider([{"items": []}])
        MODULE.run_monitor(
            provider,
            mode="once",
            poll_seconds=300,
            state_file=self.state_file,
            mark_handled=[],
            blocked_specs=[],
            increment_retry=["ci:test-suite:sha-1"],
            clear_retry=[],
            last_action_summary="Retrying CI again",
            jitter_seconds=0,
        )
        state = self.load_state()
        self.assertEqual(state["retry_counters"]["ci:test-suite:sha-1"]["count"], 2)

    def test_missing_gh_auth_yields_blocked_state(self):
        provider = FakeProvider([MODULE.WorkflowBlockedError("gh auth status failed")])

        result, _state = MODULE.run_monitor(
            provider,
            mode="once",
            poll_seconds=300,
            state_file=self.state_file,
            mark_handled=[],
            blocked_specs=[],
            increment_retry=[],
            clear_retry=[],
            last_action_summary=None,
            jitter_seconds=0,
        )

        self.assertEqual(result["status"], "blocked")
        self.assertTrue(self.state_file.exists())
        self.assertIn("gh auth status failed", result["blocked_reasons"][0]["reason"])

    def test_closed_pr_returns_closed_status(self):
        provider = FakeProvider(
            [{"context": {"state": "MERGED"}, "items": []}],
            context=make_context(state="MERGED"),
        )

        result, _state = MODULE.run_monitor(
            provider,
            mode="once",
            poll_seconds=300,
            state_file=self.state_file,
            mark_handled=[],
            blocked_specs=[],
            increment_retry=[],
            clear_retry=[],
            last_action_summary=None,
            jitter_seconds=0,
        )

        self.assertEqual(result["status"], "closed")
        self.assertEqual(result["pending_items"], [])

    def test_blocked_item_is_recorded_without_duplicate_requeue(self):
        provider = FakeProvider([{"items": [make_review_item()]}])
        MODULE.run_monitor(
            provider,
            mode="once",
            poll_seconds=300,
            state_file=self.state_file,
            mark_handled=[],
            blocked_specs=[],
            increment_retry=[],
            clear_retry=[],
            last_action_summary=None,
            jitter_seconds=0,
        )

        provider = FakeProvider([{"items": [make_review_item()]}])
        result, _state = MODULE.run_monitor(
            provider,
            mode="once",
            poll_seconds=300,
            state_file=self.state_file,
            mark_handled=[],
            blocked_specs=["review:10=Issue creation failed"],
            increment_retry=[],
            clear_retry=[],
            last_action_summary="Follow-up issue creation failed",
            jitter_seconds=0,
        )

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["new_items"], [])
        self.assertIn("Issue creation failed", result["blocked_reasons"][0]["reason"])

    def test_fetch_iteration_falls_back_when_gh_checks_conclusion_field_is_unsupported(self):
        provider = MODULE.LiveGitHubProvider("42")
        context = make_context()

        def fake_gh_json(cmd):
            if cmd[:4] == ["gh", "api", f"repos/{context['repo']}/pulls/42/reviews?per_page=100"]:
                return []
            if cmd[:4] == ["gh", "api", f"repos/{context['repo']}/issues/42/comments?per_page=100"]:
                return []
            if cmd[:4] == ["gh", "pr", "checks", "42"] and cmd[-1] == MODULE.GH_CHECK_JSON_FIELDS:
                raise MODULE.WorkflowBlockedError(
                    f'Command failed: gh pr checks 42 --json {MODULE.GH_CHECK_JSON_FIELDS}\nUnknown JSON field: "bucket"'
                )
            if cmd[:4] == ["gh", "pr", "checks", "42"] and cmd[-1] == "name,state,link,description,workflow":
                return [
                    {
                        "name": "Quality Test",
                        "state": "SUCCESS",
                        "link": "https://github.com/acme/widgets/actions/runs/1",
                        "description": "",
                        "workflow": "PR Validation",
                    }
                ]
            if cmd[:3] == ["gh", "api", "graphql"]:
                return {
                    "data": {
                        "repository": {
                            "pullRequest": {
                                "reviewThreads": {
                                    "nodes": [],
                                }
                            }
                        }
                    }
                }
            raise AssertionError(f"Unexpected gh_json command: {cmd}")

        with mock.patch.object(provider, "resolve_context", return_value=context):
            with mock.patch.object(MODULE, "gh_json", side_effect=fake_gh_json):
                iteration = provider.fetch_iteration(context, "agent")

        self.assertEqual(iteration.items, [])
        self.assertEqual(iteration.failed_checks, [])


if __name__ == "__main__":
    unittest.main()
