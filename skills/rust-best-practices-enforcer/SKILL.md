---
name: rust-best-practices-enforcer
description: Analyze Rust applications and enforce strict best practices defined by this repository's handbook chapters in book/*.md. Use when auditing or fixing Rust crates/workspaces, preparing CI quality gates, reviewing pull requests for idiomatic Rust, or generating actionable compliance reports tied to ownership, linting, performance, error handling, testing, dispatch, documentation, and pointer-safety guidance.
---

# Rust Best Practices Enforcer

Use this skill to perform repeatable Rust best-practices audits and produce fixes aligned to the handbook chapters in this repository.

## Workflow

1. Locate the target Rust project root (directory containing `Cargo.toml`).
2. Run the bundled checker in strict mode:
   ```bash
   python3 scripts/enforce_rust_best_practices.py --project-root <target-rust-project> --fail-level warning
   ```
3. Read [references/rule-matrix.md](references/rule-matrix.md) and map every finding to its chapter guidance.
4. Apply fixes in this order:
   - Blockers first (`panic!/todo!/unimplemented!/unwrap/expect` in production paths, forbidden lint suppressions).
   - Then warnings (tracking TODOs with issue ids, missing lint policy, library error ergonomics).
   - Then manual design-principles review (`references/book/chapter_10_design_principles.md`) for architecture-level violations that cannot be automated.
5. Run validation commands after edits:
   ```bash
   cargo fmt --all -- --check
   cargo clippy --all-targets --all-features -- -D warnings
   cargo test --all-targets --all-features
   ```
6. Report results as:
   - `Blockers`
   - `Warnings`
   - `Fixes applied`
   - `Residual risks`

## Enforcement Policy

- Treat blocker findings as mandatory fixes.
- Treat warning findings as mandatory when `--fail-level warning` is used.
- Treat design-principles guidance in `chapter_10_design_principles.md` as mandatory manual review checkpoints during every audit.
- Prefer code changes over lint suppression. If suppression is unavoidable, require `#[expect(...)]` with an explicit reason.
- Preserve project semantics; do not perform mechanical rewrites that alter API contracts without explicit justification.

## Chapter Loading Strategy

Read the matrix first, then load only the chapter files you need:

- Ownership, clones, options/results, comments style: `references/book/chapter_01.md`
- Lints and policy configuration: `references/book/chapter_02.md`
- Performance and allocation choices: `references/book/chapter_03.md`
- Error handling strategy: `references/book/chapter_04.md`
- Test quality and structure: `references/book/chapter_05.md`
- Static vs dynamic dispatch decisions: `references/book/chapter_06.md`
- Type-state opportunities: `references/book/chapter_07.md`
- Comments vs rustdoc discipline: `references/book/chapter_08.md`
- Pointer/thread-safety choices: `references/book/chapter_09.md`
- Closing guidance and ecosystem links: `references/book/zz_final_notes.md`
- Design principles baseline (SOLID, DRY, KISS, CQS, encapsulation, and related patterns): `references/book/chapter_10_design_principles.md`

## Resources

- `scripts/enforce_rust_best_practices.py`: Deterministic audit script (cargo gates + static rule checks).
- `references/rule-matrix.md`: Rule ids, severity, chapter links, and remediation guidance.
- `references/book/chapter_10_design_principles.md`: Design principles baseline for architecture and API shape decisions.
- `references/book/*.md`: Full handbook chapters embedded as local reference material for this skill.
