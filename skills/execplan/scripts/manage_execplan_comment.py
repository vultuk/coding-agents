#!/usr/bin/env python3
"""
Deterministic helpers for audit-heavy ExecPlan GitHub comments.

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
import json
import re
import sys
from copy import deepcopy
from pathlib import Path


MANAGED_MARKER = "<!-- execplan:managed -->"
META_START = "<!-- execplan:meta:start -->"
META_END = "<!-- execplan:meta:end -->"
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
    "Progress": "- [ ] EP-001 Replace with the next independently verifiable slice.",
    "Surprises & Discoveries": "- Observation: None yet.\n  Evidence: Add concrete proof when something unexpected appears.",
    "Decision Log": "- Decision: Not recorded yet.\n  Rationale: Replace when a real design choice is made.\n  Date/Author: 1970-01-01T00:00:00Z / pending",
    "Outcomes & Retrospective": "Summarize outcomes, remaining gaps, and lessons learned as the work progresses.",
    "Context and Orientation": "Describe the relevant repository areas as if the reader has no prior context.",
    "Plan of Work": "Describe the planned sequence of changes in prose before implementation starts.",
    "Concrete Steps": "State the exact commands to run, where to run them, and the expected success signals.",
    "Validation and Acceptance": "Describe how to prove the change works. Record only checks that actually ran.",
    "Idempotence and Recovery": "Document safe retry steps, conflict handling, and any rollback path for risky operations.",
    "Artifacts and Notes": "Include concise transcripts, diffs, or snippets that prove progress without replacing the `Progress` checkboxes.",
    "Interfaces and Dependencies": "Name the modules, services, functions, commands, or APIs that this work depends on.",
    "Audit Evidence": "Record one entry per completed slice using the fields `slice`, `time`, `kind`, `action`, `cwd`, `result`, and `proof`.",
    "Delivery Metadata": "- Branch: pending\n- Commit: pending\n- PR: pending\n- Reviewer request: pending\n- Handoff: pending\n- Validation: pending",
}


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
    return f"{META_START}\n{rendered}\n{META_END}"


def strip_metadata_block(text: str) -> tuple[str, dict]:
    pattern = re.compile(
        rf"\n?{re.escape(META_START)}\n(.*?)\n{re.escape(META_END)}\n?",
        re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        return text, {}
    payload = match.group(1)
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Failed to parse existing metadata block: {exc}") from exc
    stripped = text[: match.start()] + text[match.end() :]
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
    return [part.strip() for part in parts if part.strip()]


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic helpers for audit-heavy ExecPlan comments.")
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
    record_slice.add_argument("--time", required=True, help="UTC ISO 8601 timestamp for the completed slice and evidence entry.")
    record_slice.add_argument("--kind", choices=["context", "implementation", "validation", "review", "blocker", "delivery"], required=True)
    record_slice.add_argument("--action", required=True, help="Command or action that produced this evidence.")
    record_slice.add_argument("--cwd", required=True, help="Working directory for the command or action.")
    record_slice.add_argument("--result", required=True, help="Concise result summary.")
    record_slice.add_argument("--proof", required=True, help="Concrete proof, output snippet, or artifact reference.")
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

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
