# Rust Best Practices Rule Matrix

Use this matrix to tie enforcement findings to the source handbook.

## Automated Rules

| Rule ID | Severity | Source | What to enforce |
| --- | --- | --- | --- |
| `RBP-ERR-001` | blocker | Chapter 4.1, 4.2 | Avoid `unwrap(...)` and `expect(...)` in production code paths. |
| `RBP-ERR-002` | blocker | Chapter 4.1 | Avoid `panic!`, `todo!`, and `unimplemented!` in production code paths. |
| `RBP-LINT-001` | blocker | Chapter 2.4 | Avoid `#[allow(clippy::...)]`; prefer `#[expect(clippy::...)]` with reason. |
| `RBP-ERR-003` | warning | Chapter 4.4 | Avoid `anyhow` inside library code paths. Reserve for binaries/tests/helpers. |
| `RBP-ERR-004` | warning | Chapter 4.7 | Avoid `Box<dyn std::error::Error>` in libraries unless justified. |
| `RBP-DOC-001` | warning | Chapter 8.6 | Require issue reference on TODO comments (for example `TODO(issue #123): ...`). |
| `RBP-LINT-002` | warning | Chapter 2.5 | Configure clippy lint policy in `Cargo.toml` (`[lints.clippy]` or `[workspace.lints.clippy]`). |

## Design Principles Review Rules (Manual)

These are required during audits and should be attached to affected code paths when reporting findings.

| Rule ID | Severity | Source | What to review |
| --- | --- | --- | --- |
| `RBP-DP-001` | warning | Design Principles | Single Responsibility: does each module/type/function have one clear responsibility? |
| `RBP-DP-002` | warning | Design Principles | Open/Closed Principle: can behavior be extended by adding new variants, implementations, or composition instead of editing stable modules? |
| `RBP-DP-003` | warning | Design Principles | Liskov Substitution: do substitutable types preserve expected behavior for all callers? |
| `RBP-DP-004` | warning | Design Principles | Interface Segregation: are traits/interfaces minimal for the consumers that use them? |
| `RBP-DP-005` | warning | Design Principles | Dependency Inversion: are abstractions declared at stable boundaries and injected from upper layers? |
| `RBP-DP-006` | warning | Design Principles | DRY: can duplicated logic or repeated conditionals be consolidated safely? |
| `RBP-DP-007` | warning | Design Principles | KISS / YAGNI: are abstractions and indirections warranted by current requirements? |
| `RBP-DP-008` | warning | Design Principles | Encapsulation: are invariants guarded and internals hidden behind focused APIs? |
| `RBP-DP-009` | warning | Design Principles | Tell, Don’t Ask / Law of Demeter: is behavior invoked directly without traversing nested internals? |
| `RBP-DP-010` | warning | Design Principles | Command-Query Separation: do commands mutate state without returning values and queries avoid mutation? |

## Cargo Quality Gates

These are mandatory checks before reporting compliance:

1. `cargo fmt --all -- --check`
2. `cargo clippy --all-targets --all-features -- -D warnings`
3. `cargo test --all-targets --all-features`

## Manual Review Checklist

Use this when static checks pass but design-level review is required.

1. Chapter 1: Prefer borrowing over cloning and avoid early allocation patterns.
2. Chapter 3: Confirm "measure-first" performance work and avoid unnecessary intermediate allocations.
3. Chapter 5: Check test naming clarity, one-behavior focus, and meaningful assertions.
4. Chapter 6: Confirm static dispatch by default; justify dynamic dispatch with runtime polymorphism needs.
5. Chapter 7: Identify runtime state flags that should be represented as type-state APIs.
6. Chapter 8: Remove stale/explanatory comments that should be code or rustdoc.
7. Chapter 9: Confirm pointer/synchronization choice matches thread-safety requirements.
8. Design principles: verify SOLID, DRY, KISS, encapsulation, Tell-Dont-Ask, and CQS across module boundaries.

## Reporting Format

Return findings grouped by severity and include:

- Rule id
- File and line
- Why it violates the handbook
- Minimal safe fix
