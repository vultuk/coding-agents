# Design Principles Matrix

Use this matrix as the source of truth for strict enforcement. Evaluate all principles unless clearly `N/A`.

Rust-specific filtering result: no principle in this list is Rust-specific; all are retained as general software design principles.

## Scoring Model

- `PASS`: Meets all pass checks with evidence.
- `FAIL`: Breaks at least one pass check.
- `N/A`: Not applicable due to architecture/language construct absence.

Severity guidance:
- Default to `P1` for structural principle violations.
- Escalate to `P0` when correctness, data integrity, or security risk is direct.
- Downgrade to `P2` or `P3` only when impact is local and low risk.

## Principle Checks

### 1. Single Responsibility Principle (SRP)

Pass checks:
- Keep each module/class/function focused on one reason to change.
- Isolate unrelated policies (validation, persistence, formatting, transport).

Fail indicators:
- God objects/modules with mixed concerns.
- A single change request repeatedly touching unrelated logic in one unit.

Required evidence:
- Symbol ownership map and examples of mixed concerns.

### 2. Open/Closed Principle (OCP)

Pass checks:
- Extend behavior via composition, polymorphism, strategy/configuration, or plug-in seams.
- Avoid frequent edits to stable core logic for new variants.

Fail indicators:
- Repeated conditional branching by type/mode in core paths.
- New variants require modifying existing stable modules.

Required evidence:
- Change pattern showing "modify core" instead of "add extension."

### 3. Liskov Substitution Principle (LSP)

Pass checks:
- Subtypes preserve parent/interface contract semantics.
- Strengthen guarantees only when callers remain valid without change.

Fail indicators:
- Subtype throws/returns behavior callers cannot safely handle under parent contract.
- Preconditions tightened or postconditions weakened in subtype overrides.

Required evidence:
- Contract mismatch example at call sites.

### 4. Interface Segregation Principle (ISP)

Pass checks:
- Keep interfaces small and client-specific.
- Depend only on methods actually needed by each consumer.

Fail indicators:
- Fat interfaces forcing no-op, stub, or unsupported-method implementations.
- Consumers importing broad interfaces for a tiny subset.

Required evidence:
- Unused method footprint and forced implementation examples.

### 5. Dependency Inversion Principle (DIP)

Pass checks:
- Depend on abstractions at module boundaries.
- Inject concrete implementations at composition roots.

Fail indicators:
- High-level policy layers instantiate low-level details directly.
- Business logic tied to framework/database/transport concrete classes.

Required evidence:
- Dependency graph from high-level modules to concrete infrastructure.

### 6. Composite Reuse Principle (Composition over Inheritance)

Pass checks:
- Prefer composing capabilities over deep inheritance hierarchies.
- Use inheritance only for genuine subtype relationships with stable contracts.

Fail indicators:
- Inheritance used only for code reuse.
- Fragile base class effects and cascading override complexity.

Required evidence:
- Hierarchy depth and override behavior fragility examples.

### 7. DRY (Don't Repeat Yourself)

Pass checks:
- Keep each business rule in a single authoritative place.
- Share reusable logic where semantics are identical.

Fail indicators:
- Copy-paste logic diverging across files.
- Parallel implementations of the same policy/rule.

Required evidence:
- Duplicate logic instances and divergence risk.

### 8. KISS

Pass checks:
- Prefer the simplest design that satisfies current requirements.
- Remove speculative abstractions without proven need.

Fail indicators:
- Premature generalization, deep indirection, or needless abstraction layers.
- Complexity that does not reduce risk or improve extensibility.

Required evidence:
- Complexity-to-benefit mismatch with concrete simplification path.

### 9. Law of Demeter (LoD)

Pass checks:
- Limit navigation across object graphs.
- Expose cohesive methods instead of chain-reaching into internals.

Fail indicators:
- Long call chains (train wrecks) across foreign object internals.
- Repeated external knowledge of deep structure.

Required evidence:
- Cross-object chain examples and suggested boundary method alternatives.

### 10. Design by Contract (DbC)

Pass checks:
- Define and enforce preconditions, postconditions, and invariants.
- Fail fast on contract violations.

Fail indicators:
- Implicit assumptions not validated.
- Missing guarantees for outputs or state transitions.

Required evidence:
- Unchecked precondition/postcondition examples and invariant break risk.

### 11. Encapsulation

Pass checks:
- Restrict direct state access.
- Expose behavior-oriented APIs that protect invariants.

Fail indicators:
- Public mutable state with invariant leakage.
- External code mutating internals to maintain behavior.

Required evidence:
- Direct mutation paths and broken invariant potential.

### 12. Command-Query Separation (CQS)

Pass checks:
- Keep queries side-effect free.
- Keep commands explicit about mutation effects.

Fail indicators:
- Read-named APIs mutating state.
- Command APIs relying on return values with hidden side effects.

Required evidence:
- Method behavior mismatch against command/query intent.

### 13. Principle of Least Astonishment (POLA)

Pass checks:
- Keep naming, defaults, and behavior aligned with user/developer expectations.
- Preserve consistency with local codebase conventions.

Fail indicators:
- Surprising side effects or hidden defaults.
- API behavior contradictory to naming or common expectations.

Required evidence:
- Concrete surprise scenario and affected consumer expectations.

### 14. Linguistic-Modular-Units

Pass checks:
- Align module boundaries with language/package constructs and semantics.
- Keep modules cohesive with clear responsibility boundaries.

Fail indicators:
- Arbitrary module splits crossing language structure meaningfully.
- Logical unit fragmented across unrelated containers.

Required evidence:
- Structural mismatch between conceptual unit and language module layout.

### 15. Self-Documentation

Pass checks:
- Encode intent through names, types, boundaries, and local invariants.
- Keep critical usage expectations in module interfaces or nearby docs.
- For newly created React components, provide appropriate Storybook stories covering the primary states and intended usage.

Fail indicators:
- Opaque naming requiring external tribal knowledge.
- Hidden assumptions not discoverable from module/interface context.
- Newly created React components ship without matching Storybook stories, or the stories omit core states needed to understand intended behavior.

Required evidence:
- Example where behavior cannot be inferred from local code/interface.
- Component-to-story mapping and any missing state coverage for newly created React components.

### 16. Uniform Access

Pass checks:
- Keep client-facing access semantics consistent regardless of computed vs stored values.
- Prevent API churn from internal representation changes.

Fail indicators:
- Different usage styles that leak internal storage/computation details.
- Representation changes forcing broad caller rewrites.

Required evidence:
- Caller impact showing abstraction leakage.

### 17. Single Choice

Pass checks:
- Centralize exhaustive alternative lists in one module/point.
- Prevent scattered switch/if trees over the same alternatives.

Fail indicators:
- Repeated alternative lists duplicated across many modules.
- New variant rollout requiring edits in many unrelated places.

Required evidence:
- Variant addition path showing multi-file scattered edits.

### 18. Persistence Closure

Pass checks:
- Persist and restore dependent object graphs consistently with integrity.
- Keep loading behavior coherent for required dependents.

Fail indicators:
- Persisting root objects without required dependents.
- Rehydration producing partially valid graphs without explicit contract.

Required evidence:
- Data lifecycle example showing dependency loss or inconsistent restore.

## Exception Policy

Allow exceptions only when all conditions are met:

1. Document a concrete constraint (performance, compatibility, regulatory, platform).
2. Provide evidence that compliant alternatives were considered.
3. Add a bounded mitigation plan with owner and timeline.
4. Mark exception status explicitly as `temporary` or `permanent`.

Treat undocumented exceptions as `FAIL`.
