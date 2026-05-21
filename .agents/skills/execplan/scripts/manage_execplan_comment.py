#!/usr/bin/env python3
"""
Deterministic helpers for GitHub-hosted ExecPlan comments.

This script keeps the machine-managed portions of an ExecPlan comment stable:
- the hidden metadata block
- required section scaffolding
- progress items keyed by stable slice IDs
- per-slice audit evidence entries
- delivery metadata
- the final handoff comment body
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
from copy import deepcopy
from pathlib import Path


MANAGED_MARKER = "<!-- execplan:managed -->"
META_MARKER = "<!-- execplan:meta"
LEGACY_META_START = "<!-- execplan:meta:start -->"
LEGACY_META_END = "<!-- execplan:meta:end -->"
HANDOFF_MARKER = "<!-- execplan:handoff -->"

SECTION_ORDER = [
    "Progress",
    "Surprises & Discoveries",
    "Decision Log",
    "Outcomes & Retrospective",
    "Context and Orientation",
    "Plan of Work",
    "Concrete Steps",
    "Validation and Acceptance",
    "Idempotence and Recovery",
    "Artifacts and Notes",
    "Interfaces and Dependencies",
    "Audit Evidence",
    "Delivery Metadata",
]

SECTION_TEMPLATES = {
    "Progress": "- [ ] EP-001 Define the first independently verifiable slice.",
    "Surprises & Discoveries": "- None yet.",
    "Decision Log": "- None yet.",
    "Outcomes & Retrospective": "Pending.",
    "Context and Orientation": "Pending.",
    "Plan of Work": "Pending.",
    "Concrete Steps": "Pending.",
    "Validation and Acceptance": "Pending.",
    "Idempotence and Recovery": "Pending.",
    "Artifacts and Notes": "None yet.",
    "Interfaces and Dependencies": "Pending.",
    "Audit Evidence": "None yet.",
    "Delivery Metadata": "- Branch: pending\n- Commit: pending\n- PR: pending\n- Reviewer request: pending\n- Handoff: pending\n- Validation: pending",
}

VISIBLE_PATH_PATTERNS = [
    re.compile(r"/Users/[^\s)]+"),
    re.compile(r"/home/[^\s)]+"),
    re.compile(r"[A-Za-z]:\\\\Users\\\\[^\s)]+"),
    re.compile(r"/\.codex/worktrees/[^\s)]+"),
]


def default_metadata() -> dict:
    return {
        "issue": None,
        "repo": None,
        "mode": None,
        "status": "pending",
        "issueAuthor": None,
        "commentId": None,
        "planRevision": 0,
        "lastSyncedAt": None,
        "branch": None,
        "commit": None,
        "pr": {
            "number": None,
            "url": None,
        },
        "reviewGate": {
            "status": "pending",
            "reviewedAt": None,
            "summary": None,
            "fixesApplied": False,
            "blockers": [],
        },
        "validation": {
            "status": "pending",
            "summary": None,
            "commands": [],
        },
        "handoff": {
            "commentId": None,
            "status": "pending",
        },
    }


def deep_merge(base: dict, updates: dict) -> dict:
    result = deepcopy(base)
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def metadata_block(metadata: dict) -> str:
    rendered = json.dumps(metadata, indent=2, sort_keys=True)
    encoded = base64.b64encode(rendered.encode("utf-8")).decode("ascii")
    return f"{META_MARKER}\n{encoded}\n-->"


def _parse_metadata_payload(payload: str) -> dict:
    stripped = payload.strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    try:
        decoded = base64.b64decode(stripped, validate=True).decode("utf-8")
        return json.loads(decoded)
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Failed to parse existing metadata block: {exc}") from exc


def strip_metadata_block(text: str) -> tuple[str, dict]:
    single_comment_pattern = re.compile(
        rf"\n?{re.escape(META_MARKER)}\n(.*?)\n-->\n?",
        re.DOTALL,
    )
    match = single_comment_pattern.search(text)
    if match:
        payload = match.group(1)
        parsed = _parse_metadata_payload(payload)
        stripped = text[: match.start()] + text[match.end() :]
        return stripped, parsed

    legacy_pattern = re.compile(
        rf"\n?{re.escape(LEGACY_META_START)}\n(.*?)\n{re.escape(LEGACY_META_END)}\n?",
        re.DOTALL,
    )
    legacy_match = legacy_pattern.search(text)
    if not legacy_match:
        return text, {}
    payload = legacy_match.group(1)
    parsed = _parse_metadata_payload(payload)
    stripped = text[: legacy_match.start()] + text[legacy_match.end() :]
    return stripped, parsed


def ensure_managed_header(text: str, title: str) -> str:
    normalized = text.replace("\r\n", "\n").strip("\n")
    if not normalized:
        normalized = f"{MANAGED_MARKER}\n# {title}"
    elif MANAGED_MARKER not in normalized:
        normalized = f"{MANAGED_MARKER}\n# {title}\n\n{normalized}"
    elif not re.search(r"^# .+$", normalized, re.MULTILINE):
        normalized = normalized.replace(MANAGED_MARKER, f"{MANAGED_MARKER}\n# {title}", 1)
    return normalized.rstrip() + "\n"


def insert_metadata_block(text: str, metadata: dict) -> str:
    stripped, existing = strip_metadata_block(text)
    merged = deep_merge(default_metadata(), existing)
    merged = deep_merge(merged, metadata)
    block = metadata_block(merged)

    heading_match = re.search(r"^# .+$", stripped, re.MULTILINE)
    if heading_match:
        insert_at = heading_match.end()
        updated = stripped[:insert_at] + "\n\n" + block + stripped[insert_at:]
    else:
        marker_pos = stripped.find(MANAGED_MARKER)
        if marker_pos == -1:
            updated = block + "\n\n" + stripped
        else:
            marker_end = marker_pos + len(MANAGED_MARKER)
            updated = stripped[:marker_end] + "\n\n" + block + stripped[marker_end:]
    return updated.replace("\n\n\n", "\n\n").rstrip() + "\n"


def strip_visible_metadata(text: str) -> str:
    stripped, _ = strip_metadata_block(text)
    return stripped


def parse_sections(text: str) -> tuple[str, list[tuple[str, str]]]:
    matches = list(re.finditer(r"^## (.+)$", text, re.MULTILINE))
    if not matches:
        return text.rstrip() + "\n", []

    prefix = text[: matches[0].start()].rstrip() + "\n"
    sections: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        name = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        content = text[start:end].strip("\n")
        sections.append((name, content))
    return prefix, sections


def build_body(prefix: str, sections: list[tuple[str, str]]) -> str:
    chunks = [prefix.rstrip()]
    for name, content in sections:
        chunks.append(f"## {name}")
        chunks.append(content.strip() if content.strip() else SECTION_TEMPLATES.get(name, ""))
    return "\n\n".join(chunks).rstrip() + "\n"


def ensure_sections(text: str) -> str:
    prefix, existing_sections = parse_sections(text)
    existing_map = {name: content for name, content in existing_sections}
    existing_order = [name for name, _ in existing_sections]

    ordered_sections: list[tuple[str, str]] = []
    for name in SECTION_ORDER:
        ordered_sections.append((name, existing_map.pop(name, SECTION_TEMPLATES[name])))

    for name in existing_order:
        if name in existing_map:
            ordered_sections.append((name, existing_map.pop(name)))

    for name, content in existing_map.items():
        ordered_sections.append((name, content))

    return build_body(prefix, ordered_sections)


def replace_section(text: str, target_name: str, content: str) -> str:
    prefix, sections = parse_sections(text)
    replaced = False
    new_sections = []
    for name, current in sections:
        if name == target_name:
            new_sections.append((name, content))
            replaced = True
        else:
            new_sections.append((name, current))
    if not replaced:
        new_sections.append((target_name, content))
    return build_body(prefix, new_sections)


def get_section(text: str, target_name: str) -> str:
    _, sections = parse_sections(text)
    for name, content in sections:
        if name == target_name:
            return content
    return ""


def render_progress_line(slice_id: str, summary: str, state: str, timestamp: str | None) -> str:
    if state == "done":
        if not timestamp:
            raise SystemExit("Completed progress items require --time in UTC ISO 8601 format.")
        return f"- [x] {slice_id} ({timestamp}) {summary}"
    return f"- [ ] {slice_id} {summary}"


def upsert_progress_item(content: str, slice_id: str, summary: str, state: str, timestamp: str | None) -> str:
    line = render_progress_line(slice_id, summary, state, timestamp)
    regex = re.compile(rf"^- \[[ x]\] {re.escape(slice_id)}(?: \([^)]+\))? .+$", re.MULTILINE)
    if regex.search(content):
        updated = regex.sub(line, content, count=1)
    else:
        updated = content.strip()
        if updated:
            updated += "\n" + line
        else:
            updated = line
    return updated.strip()


def evidence_block(entry: dict[str, str]) -> str:
    return "\n".join(
        [
            f"- slice: {entry['slice']}",
            f"  time: {entry['time']}",
            f"  kind: {entry['kind']}",
            f"  action: {entry['action']}",
            f"  cwd: {entry['cwd']}",
            f"  result: {entry['result']}",
            f"  proof: {entry['proof']}",
        ]
    )


def split_evidence_entries(content: str) -> list[str]:
    stripped = content.strip()
    if not stripped:
        return []
    parts = re.split(r"\n{2,}(?=- slice: )", stripped)
    return [part.strip() for part in parts if part.strip().startswith("- slice: ")]


def upsert_evidence(content: str, entry: dict[str, str]) -> str:
    block = evidence_block(entry)
    blocks = split_evidence_entries(content)
    replaced = False
    prefix = f"- slice: {entry['slice']}\n"
    for index, current in enumerate(blocks):
        if current.startswith(prefix):
            blocks[index] = block
            replaced = True
            break
    if not replaced:
        blocks.append(block)
    return "\n\n".join(blocks).strip()


def render_delivery_metadata(args: argparse.Namespace) -> str:
    return "\n".join(
        [
            f"- Branch: {args.branch}",
            f"- Commit: {args.commit}",
            f"- PR: {args.pr}",
            f"- Reviewer request: {args.reviewer_status}",
            f"- Handoff: {args.handoff_status}",
            f"- Validation: {args.validation_summary}",
        ]
    )


def lint_visible_content(text: str) -> list[str]:
    visible = strip_visible_metadata(text)
    issues: list[str] = []
    spans: list[tuple[int, int]] = []
    for pattern in VISIBLE_PATH_PATTERNS:
        match = pattern.search(visible)
        if match:
            start, end = match.span()
            if any(not (end <= existing_start or start >= existing_end) for existing_start, existing_end in spans):
                continue
            spans.append((start, end))
            issues.append(
                "Visible plan content contains a machine-local absolute path. "
                "Use <repo-root> and repository-relative paths in the GitHub comment instead: "
                f"{match.group(0)}"
            )
    return issues


def load_metadata_updates(args: argparse.Namespace) -> dict:
    updates: dict = {}
    if getattr(args, "meta_file", None):
        updates = json.loads(Path(args.meta_file).read_text(encoding="utf-8"))
    if getattr(args, "meta_json", None):
        updates = deep_merge(updates, json.loads(args.meta_json))
    return updates


def normalize_command(args: argparse.Namespace) -> None:
    input_path = Path(args.input)
    output_path = Path(args.output or args.input)
    text = read_text(input_path) if input_path.exists() else ""
    text = ensure_managed_header(text, args.title)
    text = insert_metadata_block(text, load_metadata_updates(args))
    text = ensure_sections(text)
    write_text(output_path, text)


def record_slice_command(args: argparse.Namespace) -> None:
    path = Path(args.input)
    text = ensure_sections(insert_metadata_block(ensure_managed_header(read_text(path), args.title), load_metadata_updates(args)))

    progress = get_section(text, "Progress")
    progress = upsert_progress_item(progress, args.slice_id, args.summary, args.state, args.time)
    text = replace_section(text, "Progress", progress)

    if args.state == "done":
        if not all([args.time, args.kind, args.action, args.cwd, args.result, args.proof]):
            raise SystemExit(
                "Completed slices require --time, --kind, --action, --cwd, --result, and --proof."
            )
        entry = {
            "slice": args.slice_id,
            "time": args.time,
            "kind": args.kind,
            "action": args.action,
            "cwd": args.cwd,
            "result": args.result,
            "proof": args.proof,
        }
        audit_evidence = get_section(text, "Audit Evidence")
        audit_evidence = upsert_evidence(audit_evidence, entry)
        text = replace_section(text, "Audit Evidence", audit_evidence)
    write_text(Path(args.output or args.input), text)


def set_delivery_command(args: argparse.Namespace) -> None:
    path = Path(args.input)
    text = ensure_sections(insert_metadata_block(ensure_managed_header(read_text(path), args.title), load_metadata_updates(args)))
    delivery = render_delivery_metadata(args)
    text = replace_section(text, "Delivery Metadata", delivery)
    write_text(Path(args.output or args.input), text)


def render_handoff_command(args: argparse.Namespace) -> None:
    mention = ""
    if args.issue_author and args.viewer and args.issue_author != args.viewer:
        mention = f"@{args.issue_author} "

    body = "\n".join(
        [
            HANDOFF_MARKER,
            f"{mention}implementation for #{args.issue} is complete and ready for review.".strip(),
            "",
            f"- PR: {args.pr}",
            f"- Branch: {args.branch}",
            f"- Commit: {args.commit}",
            f"- Validation: {args.validation}",
            "",
            "The managed ExecPlan comment has been updated with the full delivery log.",
        ]
    ).rstrip() + "\n"

    if args.output:
        write_text(Path(args.output), body)
    else:
        sys.stdout.write(body)


def lint_command(args: argparse.Namespace) -> None:
    path = Path(args.input)
    issues = lint_visible_content(read_text(path))
    if issues:
        for issue in issues:
            print(issue, file=sys.stderr)
        raise SystemExit(1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic helpers for GitHub-hosted ExecPlan comments.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    normalize = subparsers.add_parser("normalize", help="Ensure the managed comment header, metadata block, and required sections exist.")
    normalize.add_argument("--input", required=True, help="Input markdown file path.")
    normalize.add_argument("--output", help="Output markdown file path. Defaults to --input.")
    normalize.add_argument("--title", default="ExecPlan", help="Fallback H1 title if the file does not already have one.")
    normalize.add_argument("--meta-file", help="JSON file containing metadata updates.")
    normalize.add_argument("--meta-json", help="Inline JSON string containing metadata updates.")
    normalize.set_defaults(func=normalize_command)

    record_slice = subparsers.add_parser("record-slice", help="Upsert one progress item and one audit evidence entry.")
    record_slice.add_argument("--input", required=True, help="Input markdown file path.")
    record_slice.add_argument("--output", help="Output markdown file path. Defaults to --input.")
    record_slice.add_argument("--title", default="ExecPlan", help="Fallback H1 title if the file does not already have one.")
    record_slice.add_argument("--meta-file", help="JSON file containing metadata updates.")
    record_slice.add_argument("--meta-json", help="Inline JSON string containing metadata updates.")
    record_slice.add_argument("--slice-id", required=True, help="Stable progress slice identifier, for example EP-001.")
    record_slice.add_argument("--summary", required=True, help="Human-readable summary for the progress item.")
    record_slice.add_argument("--state", choices=["pending", "done"], required=True, help="Progress state to render.")
    record_slice.add_argument("--time", help="UTC ISO 8601 timestamp for the completed slice and evidence entry.")
    record_slice.add_argument("--kind", choices=["context", "implementation", "validation", "review", "blocker", "delivery"])
    record_slice.add_argument("--action", help="Command or action that produced this evidence.")
    record_slice.add_argument("--cwd", help="Working directory for the command or action.")
    record_slice.add_argument("--result", help="Concise result summary.")
    record_slice.add_argument("--proof", help="Concrete proof, output snippet, or artifact reference.")
    record_slice.set_defaults(func=record_slice_command)

    set_delivery = subparsers.add_parser("set-delivery", help="Render the delivery metadata section deterministically.")
    set_delivery.add_argument("--input", required=True, help="Input markdown file path.")
    set_delivery.add_argument("--output", help="Output markdown file path. Defaults to --input.")
    set_delivery.add_argument("--title", default="ExecPlan", help="Fallback H1 title if the file does not already have one.")
    set_delivery.add_argument("--meta-file", help="JSON file containing metadata updates.")
    set_delivery.add_argument("--meta-json", help="Inline JSON string containing metadata updates.")
    set_delivery.add_argument("--branch", required=True)
    set_delivery.add_argument("--commit", required=True)
    set_delivery.add_argument("--pr", required=True)
    set_delivery.add_argument("--reviewer-status", required=True)
    set_delivery.add_argument("--handoff-status", required=True)
    set_delivery.add_argument("--validation-summary", required=True)
    set_delivery.set_defaults(func=set_delivery_command)

    render_handoff = subparsers.add_parser("render-handoff", help="Render the final idempotent handoff issue comment.")
    render_handoff.add_argument("--issue", required=True)
    render_handoff.add_argument("--issue-author")
    render_handoff.add_argument("--viewer")
    render_handoff.add_argument("--pr", required=True)
    render_handoff.add_argument("--branch", required=True)
    render_handoff.add_argument("--commit", required=True)
    render_handoff.add_argument("--validation", required=True)
    render_handoff.add_argument("--output", help="Output file path. Defaults to stdout.")
    render_handoff.set_defaults(func=render_handoff_command)

    lint = subparsers.add_parser("lint", help="Reject common GitHub comment mistakes such as machine-local absolute paths.")
    lint.add_argument("--input", required=True, help="Input markdown file path.")
    lint.set_defaults(func=lint_command)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
