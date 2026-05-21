#!/usr/bin/env python3
"""
Stateful snapshot engine for the pr-feedback-workflow skill.

Typical usage:

  python3 .agents/skills/pr-feedback-workflow/scripts/pr_feedback_loop.py --mode once
  python3 .agents/skills/pr-feedback-workflow/scripts/pr_feedback_loop.py --mode watch --poll-seconds 300
  python3 .agents/skills/pr-feedback-workflow/scripts/pr_feedback_loop.py --mode watch --poll-seconds 300 --complete-when-clean

In watch mode the helper keeps polling while the PR is idle, persists state after
every poll, and returns only when new work, a blocker, or a closed PR is detected.
With --complete-when-clean, it also returns status=complete once there is no
actionable feedback, no blocker, no failed CI, and no pending/running CI.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


STATE_VERSION = 1
MIN_POLL_SECONDS = 300
DEFAULT_POLL_SECONDS = 300
DEFAULT_JITTER_SECONDS = 120
GH_CHECK_JSON_FIELDS = "name,state,conclusion,bucket,link"
SUCCESSFUL_CHECK_STATES = {"success", "skipped", "neutral", "pass"}
PENDING_CHECK_STATES = {
    "pending",
    "queued",
    "requested",
    "waiting",
    "in_progress",
    "in progress",
    "running",
    "expected",
}
ACTIONABLE_CHECK_STATES = {
    "failure",
    "failed",
    "fail",
    "timed_out",
    "cancel",
    "cancelled",
    "canceled",
    "action_required",
    "startup_failure",
    "error",
}
ITEM_PRIORITY = {
    "thread": 0,
    "review": 1,
    "issue_comment": 2,
    "ci_failure": 3,
}


class WorkflowBlockedError(RuntimeError):
    """Raised when the workflow cannot continue without user intervention."""


@dataclass
class IterationData:
    context: dict[str, Any]
    items: list[dict[str, Any]]
    failed_checks: list[dict[str, Any]]
    pending_checks: list[dict[str, Any]]


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def short_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def slug(value: str) -> str:
    lowered = value.lower()
    chars = [char if char.isalnum() else "-" for char in lowered]
    squashed = "".join(chars)
    while "--" in squashed:
        squashed = squashed.replace("--", "-")
    return squashed.strip("-") or "item"


def truncate_line(text: str, length: int = 120) -> str:
    compact = " ".join(text.split())
    if len(compact) <= length:
        return compact
    return compact[: length - 1].rstrip() + "…"


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp_path, path)


def read_json_file(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise WorkflowBlockedError(f"State file is not valid JSON: {path} ({exc})") from exc
    if not isinstance(data, dict):
        raise WorkflowBlockedError(f"State file must contain a JSON object: {path}")
    return data


def run_command(cmd: list[str]) -> str:
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise WorkflowBlockedError(f"Required executable not found: {cmd[0]}") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        stdout = (exc.stdout or "").strip()
        detail = stderr or stdout or "unknown command failure"
        raise WorkflowBlockedError(f"Command failed: {' '.join(cmd)}\n{detail}") from exc
    return result.stdout


def gh_json(cmd: list[str]) -> Any:
    raw = run_command(cmd)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise WorkflowBlockedError(f"GitHub CLI returned invalid JSON for: {' '.join(cmd)}") from exc


def ensure_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def sort_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        items,
        key=lambda item: (
            ITEM_PRIORITY.get(item.get("type", ""), 99),
            item.get("updated_at") or "",
            item.get("key") or "",
        ),
    )


def parse_blocked_spec(spec: str) -> tuple[str, str]:
    key, separator, reason = spec.partition("=")
    if not separator or not key.strip() or not reason.strip():
        raise WorkflowBlockedError(
            "Blocked item arguments must use KEY=reason format."
        )
    return key.strip(), reason.strip()


def normalise_review_item(review: dict[str, Any], self_login: str) -> dict[str, Any] | None:
    review_id = review.get("id")
    login = str((review.get("user") or {}).get("login") or "")
    body = str(review.get("body") or "").strip()
    if not review_id or not body or login.lower() == self_login.lower():
        return None

    state = str(review.get("state") or "")
    submitted_at = review.get("submitted_at") or review.get("submittedAt")
    url = review.get("html_url") or review.get("url")
    return {
        "key": f"review:{review_id}",
        "type": "review",
        "review_id": str(review_id),
        "body_hash": short_hash(body),
        "author": login,
        "summary": truncate_line(body),
        "state": state,
        "body": body,
        "updated_at": submitted_at,
        "url": url,
    }


def normalise_issue_comment(comment: dict[str, Any], self_login: str) -> dict[str, Any] | None:
    comment_id = comment.get("id")
    login = str((comment.get("user") or {}).get("login") or "")
    body = str(comment.get("body") or "").strip()
    if not comment_id or not body or login.lower() == self_login.lower():
        return None

    updated_at = comment.get("updated_at") or comment.get("updatedAt") or comment.get("created_at")
    return {
        "key": f"issue-comment:{comment_id}",
        "type": "issue_comment",
        "comment_id": str(comment_id),
        "body_hash": short_hash(body),
        "author": login,
        "summary": truncate_line(body),
        "body": body,
        "updated_at": updated_at,
        "url": comment.get("html_url") or comment.get("url"),
    }


def normalise_thread_item(thread: dict[str, Any], self_login: str) -> dict[str, Any] | None:
    thread_id = thread.get("id")
    if not thread_id or thread.get("isResolved"):
        return None

    comments = ensure_list(((thread.get("comments") or {}).get("nodes")))
    foreign_comments: list[dict[str, Any]] = []
    comment_ids: list[str] = []
    latest_updated_at: str | None = None

    for comment in comments:
        login = str(((comment.get("author") or {}).get("login")) or "")
        if not login or login.lower() == self_login.lower():
            continue
        body = str(comment.get("body") or "").strip()
        if not body:
            continue
        updated_at = comment.get("updatedAt") or comment.get("createdAt")
        database_id = comment.get("databaseId") or comment.get("id")
        if database_id:
            comment_ids.append(str(database_id))
        latest_updated_at = max(filter(None, [latest_updated_at, updated_at]), default=latest_updated_at)
        foreign_comments.append(
            {
                "author": login,
                "body": body,
                "updated_at": updated_at,
                "id": str(database_id) if database_id else None,
                "url": comment.get("url"),
            }
        )

    if not foreign_comments:
        return None

    signature_parts = [
        f"{entry.get('id') or ''}|{entry['author']}|{entry['updated_at'] or ''}|{entry['body']}"
        for entry in foreign_comments
    ]
    last_comment = foreign_comments[-1]
    return {
        "key": f"thread:{thread_id}",
        "type": "thread",
        "thread_id": str(thread_id),
        "comment_ids": comment_ids,
        "body_hash": short_hash("\n".join(signature_parts)),
        "author": last_comment["author"],
        "summary": truncate_line(last_comment["body"]),
        "body": "\n\n".join(entry["body"] for entry in foreign_comments),
        "updated_at": latest_updated_at,
        "url": last_comment.get("url"),
    }


def normalise_check_item(check: dict[str, Any], head_sha: str) -> dict[str, Any] | None:
    name = str(check.get("name") or "").strip()
    if not name:
        return None

    state = str(check.get("state") or "").strip().lower()
    conclusion = str(check.get("conclusion") or check.get("bucket") or "").strip().lower()
    terminal = conclusion or state
    if terminal in SUCCESSFUL_CHECK_STATES or terminal == "pending":
        return None
    if terminal not in ACTIONABLE_CHECK_STATES and state not in ACTIONABLE_CHECK_STATES:
        return None

    failure_class = slug(name)
    key = f"ci:{failure_class}:{head_sha}"
    summary = f"{name} ({conclusion or state or 'failure'})"
    return {
        "key": key,
        "type": "ci_failure",
        "failure_class": failure_class,
        "head_sha": head_sha,
        "check_name": name,
        "body_hash": short_hash(f"{name}|{state}|{conclusion}|{head_sha}"),
        "summary": summary,
        "state": state,
        "conclusion": conclusion,
        "updated_at": iso_now(),
        "url": check.get("link"),
    }


def normalise_pending_check_item(check: dict[str, Any], head_sha: str) -> dict[str, Any] | None:
    name = str(check.get("name") or "").strip()
    if not name:
        return None

    state = str(check.get("state") or "").strip().lower()
    conclusion = str(check.get("conclusion") or check.get("bucket") or "").strip().lower()
    terminal = conclusion or state
    if terminal in SUCCESSFUL_CHECK_STATES or terminal in ACTIONABLE_CHECK_STATES:
        return None
    if state not in PENDING_CHECK_STATES and terminal not in PENDING_CHECK_STATES:
        return None

    return {
        "key": f"ci-pending:{slug(name)}:{head_sha}",
        "type": "ci_pending",
        "head_sha": head_sha,
        "check_name": name,
        "summary": f"{name} ({conclusion or state or 'pending'})",
        "state": state,
        "conclusion": conclusion,
        "updated_at": iso_now(),
        "url": check.get("link"),
    }


def normalise_iteration_data(
    context: dict[str, Any],
    reviews: list[dict[str, Any]],
    issue_comments: list[dict[str, Any]],
    threads: list[dict[str, Any]],
    checks: list[dict[str, Any]],
    self_login: str,
) -> IterationData:
    items: list[dict[str, Any]] = []
    failed_checks: list[dict[str, Any]] = []
    pending_checks: list[dict[str, Any]] = []
    head_sha = str(context.get("head_sha") or "")

    for review in reviews:
        item = normalise_review_item(review, self_login)
        if item:
            items.append(item)

    for comment in issue_comments:
        item = normalise_issue_comment(comment, self_login)
        if item:
            items.append(item)

    for thread in threads:
        item = normalise_thread_item(thread, self_login)
        if item:
            items.append(item)

    for check in checks:
        item = normalise_check_item(check, head_sha)
        if item:
            items.append(item)
            failed_checks.append(item)
        pending_item = normalise_pending_check_item(check, head_sha)
        if pending_item:
            pending_checks.append(pending_item)

    return IterationData(
        context=context,
        items=sort_items(items),
        failed_checks=sort_items(failed_checks),
        pending_checks=sort_items(pending_checks),
    )


class LiveGitHubProvider:
    def __init__(self, selector: str | None) -> None:
        self.selector = selector

    def resolve_repo(self) -> dict[str, str]:
        repo = gh_json(["gh", "repo", "view", "--json", "nameWithOwner"])
        name_with_owner = str(repo.get("nameWithOwner") or "")
        if "/" not in name_with_owner:
            raise WorkflowBlockedError("Unable to resolve repository from current directory.")
        owner, name = name_with_owner.split("/", 1)
        return {
            "name_with_owner": name_with_owner,
            "owner": owner,
            "name": name,
        }

    def resolve_self_login(self) -> str:
        user = gh_json(["gh", "api", "user"])
        login = str(user.get("login") or "")
        if not login:
            raise WorkflowBlockedError("Unable to resolve GitHub login from gh auth.")
        return login

    def resolve_context(self) -> dict[str, Any]:
        cmd = [
            "gh",
            "pr",
            "view",
            "--json",
            "number,url,title,state,headRefName,baseRefName,headRefOid",
        ]
        if self.selector:
            cmd.append(self.selector)
        data = gh_json(cmd)
        number = data.get("number")
        if not number:
            raise WorkflowBlockedError("No pull request could be resolved from the current branch.")

        repo = self.resolve_repo()
        return {
            "repo": repo["name_with_owner"],
            "owner": repo["owner"],
            "name": repo["name"],
            "number": int(number),
            "url": data.get("url"),
            "title": data.get("title"),
            "state": data.get("state"),
            "head_sha": data.get("headRefOid"),
            "head_ref": data.get("headRefName"),
            "base_ref": data.get("baseRefName"),
        }

    def fetch_iteration(self, context: dict[str, Any], self_login: str) -> IterationData:
        current_context = self.resolve_context()
        repo = current_context["repo"]
        pr_number = current_context["number"]
        selector = self.selector or str(pr_number)

        reviews = ensure_list(
            gh_json(["gh", "api", f"repos/{repo}/pulls/{pr_number}/reviews?per_page=100"])
        )
        issue_comments = ensure_list(
            gh_json(["gh", "api", f"repos/{repo}/issues/{pr_number}/comments?per_page=100"])
        )
        try:
            checks = ensure_list(
                gh_json(
                    [
                        "gh",
                        "pr",
                        "checks",
                        selector,
                        "--json",
                        GH_CHECK_JSON_FIELDS,
                    ]
                )
            )
        except WorkflowBlockedError as exc:
            # Some gh builds do not expose every `gh pr checks` JSON field.
            if "Unknown JSON field:" not in str(exc):
                raise
            checks = ensure_list(
                gh_json(
                    [
                        "gh",
                        "pr",
                        "checks",
                        selector,
                        "--json",
                        "name,state,link,description,workflow",
                    ]
                )
            )

        thread_query = """
query($owner:String!, $repo:String!, $pr:Int!) {
  repository(owner:$owner, name:$repo) {
    pullRequest(number:$pr) {
      reviewThreads(first:100) {
        nodes {
          id
          isResolved
          comments(first:50) {
            nodes {
              id
              databaseId
              body
              createdAt
              updatedAt
              url
              author {
                login
              }
            }
          }
        }
      }
    }
  }
}
""".strip()
        thread_payload = gh_json(
            [
                "gh",
                "api",
                "graphql",
                "-f",
                f"query={thread_query}",
                "-F",
                f"owner={current_context['owner']}",
                "-F",
                f"repo={current_context['name']}",
                "-F",
                f"pr={pr_number}",
            ]
        )
        threads = ensure_list(
            (
                (
                    ((thread_payload.get("data") or {}).get("repository") or {}).get("pullRequest") or {}
                ).get("reviewThreads")
                or {}
            ).get("nodes")
        )

        return normalise_iteration_data(current_context, reviews, issue_comments, threads, checks, self_login)


def resolve_git_dir() -> Path:
    path = run_command(["git", "rev-parse", "--git-dir"]).strip()
    if not path:
        raise WorkflowBlockedError("Unable to resolve git directory.")
    return Path(path).resolve()


def default_state_path(pr_number: int) -> Path:
    return resolve_git_dir() / "codex" / "pr-feedback-workflow" / f"pr-{pr_number}.json"


def coerce_state(context: dict[str, Any], poll_seconds: int, state: dict[str, Any]) -> dict[str, Any]:
    coerced = {
        "version": STATE_VERSION,
        "repo": context["repo"],
        "pr_number": context["number"],
        "pr_state": context["state"],
        "loop_iteration": int(state.get("loop_iteration") or 0),
        "last_poll_at": state.get("last_poll_at"),
        "handled_review_ids": list(dict.fromkeys(str(value) for value in state.get("handled_review_ids", []))),
        "handled_comment_ids": list(dict.fromkeys(str(value) for value in state.get("handled_comment_ids", []))),
        "handled_thread_ids": list(dict.fromkeys(str(value) for value in state.get("handled_thread_ids", []))),
        "handled_body_hashes": dict(state.get("handled_body_hashes") or {}),
        "handled_ci_failures": dict(state.get("handled_ci_failures") or {}),
        "pending_items": ensure_list(state.get("pending_items")),
        "blocked_items": ensure_list(state.get("blocked_items")),
        "retry_counters": dict(state.get("retry_counters") or {}),
        "last_action_summary": state.get("last_action_summary"),
        "last_status": state.get("last_status"),
        "poll_seconds": poll_seconds,
        "current_items_by_key": dict(state.get("current_items_by_key") or {}),
        "snapshot_body_hashes": dict(state.get("snapshot_body_hashes") or {}),
    }
    return coerced


def item_lookup(state: dict[str, Any]) -> dict[str, Any]:
    current = dict(state.get("current_items_by_key") or {})
    for pending in ensure_list(state.get("pending_items")):
        key = pending.get("key")
        if key and key not in current:
            current[key] = pending
    return current


def mark_item_handled(state: dict[str, Any], key: str, now: str) -> None:
    items = item_lookup(state)
    item = items.get(key)
    if not item:
        raise WorkflowBlockedError(f"Cannot mark unknown item as handled: {key}")

    handled_hashes = state.setdefault("handled_body_hashes", {})
    handled_hashes[key] = item.get("body_hash")
    state["pending_items"] = [entry for entry in ensure_list(state.get("pending_items")) if entry.get("key") != key]
    state["blocked_items"] = [entry for entry in ensure_list(state.get("blocked_items")) if entry.get("key") != key]

    item_type = item.get("type")
    if item_type == "review" and item.get("review_id"):
        state["handled_review_ids"] = list(
            dict.fromkeys(ensure_list(state.get("handled_review_ids")) + [item["review_id"]])
        )
    if item_type == "thread" and item.get("thread_id"):
        state["handled_thread_ids"] = list(
            dict.fromkeys(ensure_list(state.get("handled_thread_ids")) + [item["thread_id"]])
        )
        combined = ensure_list(state.get("handled_comment_ids")) + ensure_list(item.get("comment_ids"))
        state["handled_comment_ids"] = list(dict.fromkeys(str(value) for value in combined if value))
    if item_type == "issue_comment" and item.get("comment_id"):
        combined = ensure_list(state.get("handled_comment_ids")) + [item["comment_id"]]
        state["handled_comment_ids"] = list(dict.fromkeys(str(value) for value in combined))
    if item_type == "ci_failure":
        handled_ci = dict(state.get("handled_ci_failures") or {})
        handled_ci[key] = {
            "failure_class": item.get("failure_class"),
            "head_sha": item.get("head_sha"),
            "handled_at": now,
            "body_hash": item.get("body_hash"),
        }
        state["handled_ci_failures"] = handled_ci


def record_blocked_item(state: dict[str, Any], key: str, reason: str, now: str) -> None:
    items = item_lookup(state)
    item = items.get(key)
    if not item:
        raise WorkflowBlockedError(f"Cannot block unknown item: {key}")

    blocked_items = [entry for entry in ensure_list(state.get("blocked_items")) if entry.get("key") != key]
    blocked_items.append(
        {
            "key": key,
            "reason": reason,
            "recorded_at": now,
            "body_hash": item.get("body_hash"),
            "url": item.get("url"),
            "summary": item.get("summary"),
        }
    )
    state["blocked_items"] = sort_items(blocked_items)
    state.setdefault("handled_body_hashes", {})[key] = item.get("body_hash")
    state["pending_items"] = [entry for entry in ensure_list(state.get("pending_items")) if entry.get("key") != key]


def update_retry_counter(state: dict[str, Any], key: str, increment: bool, now: str) -> None:
    counters = dict(state.get("retry_counters") or {})
    if not increment:
        counters.pop(key, None)
        state["retry_counters"] = counters
        return

    current = dict(counters.get(key) or {})
    count = int(current.get("count") or 0) + 1
    delay = min(1800, 60 * (2 ** (count - 1)))
    next_retry_at = (
        datetime.now(timezone.utc).replace(microsecond=0) + timedelta(seconds=delay)
    ).isoformat().replace("+00:00", "Z")
    current.update(
        {
            "count": count,
            "last_attempt_at": now,
            "next_retry_at": next_retry_at,
        }
    )
    counters[key] = current
    state["retry_counters"] = counters


def apply_state_updates(
    state: dict[str, Any],
    mark_handled: list[str],
    blocked_specs: list[str],
    increment_retry: list[str],
    clear_retry: list[str],
    last_action_summary: str | None,
    now: str,
) -> None:
    for key in mark_handled:
        mark_item_handled(state, key, now)

    for spec in blocked_specs:
        key, reason = parse_blocked_spec(spec)
        record_blocked_item(state, key, reason, now)

    for key in increment_retry:
        update_retry_counter(state, key, increment=True, now=now)

    for key in clear_retry:
        update_retry_counter(state, key, increment=False, now=now)

    if last_action_summary is not None:
        state["last_action_summary"] = {
            "summary": last_action_summary,
            "at": now,
        }


def classify_items(
    state: dict[str, Any],
    items: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    handled_hashes = dict(state.get("handled_body_hashes") or {})
    previous_hashes = dict(state.get("snapshot_body_hashes") or {})
    blocked_lookup = {
        entry.get("key"): entry
        for entry in ensure_list(state.get("blocked_items"))
        if entry.get("key")
    }

    new_items: list[dict[str, Any]] = []
    updated_items: list[dict[str, Any]] = []
    blocked_items: list[dict[str, Any]] = []

    for item in items:
        key = item["key"]
        current_hash = item.get("body_hash")
        blocked = blocked_lookup.get(key)
        if blocked and blocked.get("body_hash") == current_hash:
            blocked_items.append(
                {
                    "key": key,
                    "reason": blocked.get("reason"),
                    "url": item.get("url"),
                    "summary": item.get("summary"),
                }
            )
            continue

        if handled_hashes.get(key) == current_hash:
            continue

        seen_before = key in previous_hashes or key in handled_hashes or key in blocked_lookup
        target = updated_items if seen_before else new_items
        target.append(item)

    return sort_items(new_items), sort_items(updated_items), sort_items(blocked_items)


def refresh_blocked_items(state: dict[str, Any], current_items: list[dict[str, Any]]) -> None:
    current_hash_lookup = {item["key"]: item.get("body_hash") for item in current_items}
    refreshed: list[dict[str, Any]] = []
    for entry in ensure_list(state.get("blocked_items")):
        key = entry.get("key")
        if not key:
            continue
        if key in current_hash_lookup and current_hash_lookup[key] == entry.get("body_hash"):
            refreshed.append(entry)
    state["blocked_items"] = sort_items(refreshed)


def process_iteration(
    state: dict[str, Any],
    iteration: IterationData,
    state_file: Path,
    now: str,
    complete_when_clean: bool = False,
) -> dict[str, Any]:
    context = iteration.context
    state["repo"] = context["repo"]
    state["pr_number"] = context["number"]
    state["pr_state"] = context["state"]
    state["loop_iteration"] = int(state.get("loop_iteration") or 0) + 1
    state["last_poll_at"] = now

    if str(context.get("state") or "").upper() not in {"OPEN"}:
        state["pending_items"] = []
        state["current_items_by_key"] = {}
        state["snapshot_body_hashes"] = {}
        state["last_status"] = "closed"
        return {
            "pr": context,
            "iteration": state["loop_iteration"],
            "status": "closed",
            "new_items": [],
            "updated_items": [],
            "failed_checks": [],
            "pending_checks": [],
            "blocked_reasons": [],
            "state_file": str(state_file),
            "pending_items": [],
            "last_action_summary": state.get("last_action_summary"),
        }

    current_items = sort_items(iteration.items)
    refresh_blocked_items(state, current_items)
    new_items, updated_items, blocked_items = classify_items(state, current_items)
    pending_items = sort_items(new_items + updated_items)

    state["pending_items"] = pending_items
    state["current_items_by_key"] = {item["key"]: item for item in current_items}
    state["snapshot_body_hashes"] = {item["key"]: item.get("body_hash") for item in current_items}

    if pending_items:
        status = "actionable"
    elif blocked_items:
        status = "blocked"
    elif complete_when_clean and not iteration.pending_checks:
        status = "complete"
    else:
        status = "idle"

    state["last_status"] = status
    return {
        "pr": context,
        "iteration": state["loop_iteration"],
        "status": status,
        "new_items": new_items,
        "updated_items": updated_items,
        "failed_checks": iteration.failed_checks,
        "pending_checks": iteration.pending_checks,
        "blocked_reasons": blocked_items,
        "state_file": str(state_file),
        "pending_items": pending_items,
        "last_action_summary": state.get("last_action_summary"),
        "retry_counters": state.get("retry_counters"),
    }


def blocked_result(
    state: dict[str, Any],
    context: dict[str, Any],
    state_file: Path,
    reason: str,
) -> dict[str, Any]:
    state["pr_state"] = context.get("state")
    state["repo"] = context.get("repo")
    state["pr_number"] = context.get("number")
    state["last_status"] = "blocked"
    state["last_poll_at"] = iso_now()
    return {
        "pr": context,
        "iteration": state.get("loop_iteration", 0),
        "status": "blocked",
        "new_items": [],
        "updated_items": [],
        "failed_checks": [],
        "pending_checks": [],
        "blocked_reasons": [{"key": "workflow", "reason": reason}],
        "state_file": str(state_file),
        "pending_items": ensure_list(state.get("pending_items")),
        "last_action_summary": state.get("last_action_summary"),
        "retry_counters": state.get("retry_counters"),
    }


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return read_json_file(path)


def save_state(path: Path, state: dict[str, Any]) -> None:
    atomic_write_json(path, state)


def run_monitor(
    provider: Any,
    *,
    initial_context: dict[str, Any] | None = None,
    mode: str,
    poll_seconds: int,
    state_file: Path,
    mark_handled: list[str],
    blocked_specs: list[str],
    increment_retry: list[str],
    clear_retry: list[str],
    last_action_summary: str | None,
    jitter_seconds: int,
    complete_when_clean: bool = False,
    sleep_fn: Any = time.sleep,
    randrange_fn: Any = random.randint,
) -> tuple[dict[str, Any], dict[str, Any]]:
    context = initial_context or provider.resolve_context()
    state = coerce_state(context, poll_seconds, load_state(state_file))
    now = iso_now()
    apply_state_updates(
        state,
        mark_handled=mark_handled,
        blocked_specs=blocked_specs,
        increment_retry=increment_retry,
        clear_retry=clear_retry,
        last_action_summary=last_action_summary,
        now=now,
    )
    save_state(state_file, state)

    self_login = provider.resolve_self_login()
    while True:
        try:
            iteration = provider.fetch_iteration(context, self_login)
            context = iteration.context
            result = process_iteration(
                state,
                iteration,
                state_file,
                iso_now(),
                complete_when_clean=complete_when_clean,
            )
        except WorkflowBlockedError as exc:
            result = blocked_result(state, context, state_file, str(exc))
            save_state(state_file, state)
            return result, state

        save_state(state_file, state)
        if mode == "once" or result["status"] != "idle":
            return result, state

        extra_sleep = randrange_fn(0, jitter_seconds) if jitter_seconds > 0 else 0
        sleep_fn(poll_seconds + extra_sleep)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Stateful PR feedback polling helper.")
    parser.add_argument("--pr", help="PR number or URL. Defaults to the current branch PR.")
    parser.add_argument("--mode", choices=["watch", "once"], default="watch")
    parser.add_argument(
        "--poll-seconds",
        type=int,
        default=DEFAULT_POLL_SECONDS,
        help=f"Polling interval in seconds. Minimum {MIN_POLL_SECONDS}.",
    )
    parser.add_argument(
        "--state-file",
        help="Optional path to the persisted workflow state JSON file.",
    )
    parser.add_argument(
        "--mark-handled",
        action="append",
        default=[],
        help="Item key to mark as handled before the next snapshot. Repeat for multiple items.",
    )
    parser.add_argument(
        "--record-blocked",
        action="append",
        default=[],
        help="Record a blocker as KEY=reason. Repeat for multiple blocked items.",
    )
    parser.add_argument(
        "--increment-retry",
        action="append",
        default=[],
        help="Increment retry state for the given item key.",
    )
    parser.add_argument(
        "--clear-retry",
        action="append",
        default=[],
        help="Clear retry state for the given item key.",
    )
    parser.add_argument(
        "--set-last-action",
        help="Short summary of the action taken since the previous helper invocation.",
    )
    parser.add_argument(
        "--jitter-seconds",
        type=int,
        default=DEFAULT_JITTER_SECONDS,
        help="Maximum random jitter added to idle sleeps in watch mode.",
    )
    parser.add_argument(
        "--complete-when-clean",
        action="store_true",
        help="Return status=complete instead of staying idle when there is no actionable feedback, no blockers, and no pending CI.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.poll_seconds < MIN_POLL_SECONDS:
        parser.error(f"--poll-seconds must be at least {MIN_POLL_SECONDS}.")
    if args.jitter_seconds < 0:
        parser.error("--jitter-seconds cannot be negative.")

    try:
        provider = LiveGitHubProvider(args.pr)
        context = provider.resolve_context()
        state_file = Path(args.state_file).resolve() if args.state_file else default_state_path(context["number"])
        result, _state = run_monitor(
            provider,
            initial_context=context,
            mode=args.mode,
            poll_seconds=args.poll_seconds,
            state_file=state_file,
            mark_handled=args.mark_handled,
            blocked_specs=args.record_blocked,
            increment_retry=args.increment_retry,
            clear_retry=args.clear_retry,
            last_action_summary=args.set_last_action,
            jitter_seconds=args.jitter_seconds,
            complete_when_clean=args.complete_when_clean,
        )
    except WorkflowBlockedError as exc:
        blocked = {
            "status": "blocked",
            "pending_checks": [],
            "blocked_reasons": [{"key": "workflow", "reason": str(exc)}],
        }
        print(json.dumps(blocked, indent=2, sort_keys=True))
        sys.exit(1)

    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
