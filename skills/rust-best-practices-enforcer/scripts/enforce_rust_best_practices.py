#!/usr/bin/env python3
"""
Audit a Rust project against handbook-driven best-practice checks.

This script intentionally focuses on high-confidence, automatable rules.
Use the companion rule matrix for manual design-level review.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

EXCLUDED_DIRS = {".git", ".idea", ".vscode", "target", "tests", "benches", "examples"}
TODO_TRACKING_RE = re.compile(r"TODO\s*\(\s*(?:issue|gh|jira|ticket|#)[^)]*\)", re.IGNORECASE)


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: str
    chapter: str
    file: Path
    line_no: int
    message: str
    snippet: str


@dataclass(frozen=True)
class CommandResult:
    name: str
    command: list[str]
    return_code: int
    stdout: str
    stderr: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Enforce Rust best practices using cargo checks and static scans."
    )
    parser.add_argument(
        "--project-root",
        default=".",
        help="Rust project root containing Cargo.toml (default: current directory).",
    )
    parser.add_argument(
        "--fail-level",
        choices=["blocker", "warning"],
        default="blocker",
        help="Lowest severity that causes non-zero exit status.",
    )
    parser.add_argument("--skip-fmt", action="store_true", help="Skip cargo fmt check.")
    parser.add_argument("--skip-clippy", action="store_true", help="Skip cargo clippy check.")
    parser.add_argument("--skip-tests", action="store_true", help="Skip cargo test check.")
    return parser.parse_args()


def run_command(name: str, command: list[str], cwd: Path) -> CommandResult:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        return CommandResult(
            name=name,
            command=command,
            return_code=completed.returncode,
            stdout=completed.stdout.strip(),
            stderr=completed.stderr.strip(),
        )
    except FileNotFoundError:
        return CommandResult(
            name=name,
            command=command,
            return_code=127,
            stdout="",
            stderr=f"command not found: {command[0]}",
        )


def should_scan(path: Path) -> bool:
    if path.suffix != ".rs":
        return False
    return not any(part in EXCLUDED_DIRS for part in path.parts)


def nearest_crate_root(path: Path, project_root: Path) -> Path | None:
    current = path.parent
    while current != project_root.parent:
        if (current / "Cargo.toml").exists():
            return current
        if current == project_root:
            break
        current = current.parent
    return None


def is_library_source(path: Path, project_root: Path) -> bool:
    crate_root = nearest_crate_root(path, project_root)
    if crate_root is None:
        return False

    lib_rs = crate_root / "src" / "lib.rs"
    if not lib_rs.exists():
        return False

    try:
        relative = path.relative_to(crate_root / "src")
    except ValueError:
        return False

    if relative.parts and relative.parts[0] == "bin":
        return False

    if relative == Path("main.rs"):
        return False

    return True


def scan_file(path: Path, project_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    skip_next_test_mod = False
    in_test_mod = False
    test_mod_depth = 0
    library_source = is_library_source(path, project_root)

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        snippet = stripped[:160]

        if stripped.startswith("#[cfg(test)]"):
            skip_next_test_mod = True
            continue

        if skip_next_test_mod and stripped.startswith("mod ") and "{" in line:
            in_test_mod = True
            test_mod_depth = line.count("{") - line.count("}")
            skip_next_test_mod = False
            continue

        if in_test_mod:
            test_mod_depth += line.count("{") - line.count("}")
            if test_mod_depth <= 0:
                in_test_mod = False
            continue

        if "rbp:allow" in line:
            continue

        if re.search(r"#\s*\[\s*allow\s*\(\s*clippy::", line):
            findings.append(
                Finding(
                    rule_id="RBP-LINT-001",
                    severity="blocker",
                    chapter="2.4",
                    file=path,
                    line_no=idx,
                    message="Replace #[allow(clippy::...)] with #[expect(clippy::...)] and a reason.",
                    snippet=snippet,
                )
            )

        if re.search(r"\b(?:unwrap|expect)\s*\(", line) and "unwrap_err(" not in line:
            findings.append(
                Finding(
                    rule_id="RBP-ERR-001",
                    severity="blocker",
                    chapter="4.2 / 1.3",
                    file=path,
                    line_no=idx,
                    message="Avoid unwrap/expect in production paths; propagate or map errors explicitly.",
                    snippet=snippet,
                )
            )

        if re.search(r"\b(?:panic|todo|unimplemented)\s*!\s*\(", line):
            findings.append(
                Finding(
                    rule_id="RBP-ERR-002",
                    severity="blocker",
                    chapter="4.1",
                    file=path,
                    line_no=idx,
                    message="Avoid panic/todo/unimplemented in production paths.",
                    snippet=snippet,
                )
            )

        if "TODO" in line and stripped.startswith("//") and not TODO_TRACKING_RE.search(line):
            findings.append(
                Finding(
                    rule_id="RBP-DOC-001",
                    severity="warning",
                    chapter="8.6",
                    file=path,
                    line_no=idx,
                    message="Track TODOs with a linked issue id, for example TODO(issue #123).",
                    snippet=snippet,
                )
            )

        if library_source and re.search(r"\banyhow\b", line):
            findings.append(
                Finding(
                    rule_id="RBP-ERR-003",
                    severity="warning",
                    chapter="4.4",
                    file=path,
                    line_no=idx,
                    message="Avoid anyhow in libraries; prefer explicit error types with thiserror.",
                    snippet=snippet,
                )
            )

        if library_source and re.search(
            r"Box\s*<\s*dyn\s+std::error::Error", line
        ):
            findings.append(
                Finding(
                    rule_id="RBP-ERR-004",
                    severity="warning",
                    chapter="4.7",
                    file=path,
                    line_no=idx,
                    message="Avoid Box<dyn std::error::Error> in libraries unless explicitly justified.",
                    snippet=snippet,
                )
            )

    return findings


def scan_lint_policy(project_root: Path) -> list[Finding]:
    cargo_toml = project_root / "Cargo.toml"
    if not cargo_toml.exists():
        return []

    text = cargo_toml.read_text(encoding="utf-8")
    findings: list[Finding] = []
    has_table = "[lints.clippy]" in text or "[workspace.lints.clippy]" in text
    has_deny_all = re.search(r'^\s*all\s*=\s*\{\s*level\s*=\s*"deny"', text, re.MULTILINE)

    if not has_table:
        findings.append(
            Finding(
                rule_id="RBP-LINT-002",
                severity="warning",
                chapter="2.5",
                file=cargo_toml,
                line_no=1,
                message="Add clippy lint policy table in Cargo.toml.",
                snippet="[lints.clippy] or [workspace.lints.clippy]",
            )
        )
    elif not has_deny_all:
        findings.append(
            Finding(
                rule_id="RBP-LINT-002",
                severity="warning",
                chapter="2.5",
                file=cargo_toml,
                line_no=1,
                message='Consider setting `all = { level = "deny", ... }` in clippy lint policy.',
                snippet="Missing deny baseline for clippy::all",
            )
        )

    return findings


def severity_rank(level: str) -> int:
    order = {"warning": 1, "blocker": 2}
    return order[level]


def should_fail(finding_level: str, fail_level: str) -> bool:
    return severity_rank(finding_level) >= severity_rank(fail_level)


def print_command_result(result: CommandResult) -> None:
    status = "PASS" if result.return_code == 0 else "FAIL"
    command_display = " ".join(result.command)
    print(f"[{status}] {result.name}: {command_display}")
    if result.return_code != 0:
        output = "\n".join(x for x in [result.stdout, result.stderr] if x)
        if output:
            print(output)


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).resolve()

    if not (project_root / "Cargo.toml").exists():
        print(f"error: {project_root} does not contain Cargo.toml", file=sys.stderr)
        return 2

    command_results: list[CommandResult] = []
    cargo_lock = project_root / "Cargo.lock"
    locked = ["--locked"] if cargo_lock.exists() else []

    if not args.skip_fmt:
        command_results.append(
            run_command("cargo-fmt", ["cargo", "fmt", "--all", "--", "--check"], project_root)
        )
    if not args.skip_clippy:
        command_results.append(
            run_command(
                "cargo-clippy",
                [
                    "cargo",
                    "clippy",
                    "--all-targets",
                    "--all-features",
                    *locked,
                    "--",
                    "-D",
                    "warnings",
                ],
                project_root,
            )
        )
    if not args.skip_tests:
        command_results.append(
            run_command(
                "cargo-test",
                ["cargo", "test", "--all-targets", "--all-features", *locked],
                project_root,
            )
        )

    for result in command_results:
        print_command_result(result)

    findings: list[Finding] = []
    for file_path in project_root.rglob("*.rs"):
        if should_scan(file_path):
            findings.extend(scan_file(file_path, project_root))
    findings.extend(scan_lint_policy(project_root))

    blockers = [f for f in findings if f.severity == "blocker"]
    warnings = [f for f in findings if f.severity == "warning"]

    print()
    print("Findings:")
    if not findings:
        print("  none")
    else:
        sorted_findings = sorted(
            findings,
            key=lambda f: (severity_rank(f.severity), str(f.file), f.line_no),
            reverse=True,
        )
        for finding in sorted_findings:
            location = f"{finding.file}:{finding.line_no}"
            print(
                f"  - [{finding.severity}] {finding.rule_id} ({finding.chapter}) {location}: {finding.message}"
            )
            print(f"    snippet: {finding.snippet}")

    command_failed = any(result.return_code != 0 for result in command_results)
    finding_failed = any(should_fail(f.severity, args.fail_level) for f in findings)

    print()
    print(
        "Summary: "
        f"{len(blockers)} blocker(s), {len(warnings)} warning(s), "
        f"{sum(1 for x in command_results if x.return_code != 0)} failed command(s)"
    )

    if command_failed or finding_failed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
