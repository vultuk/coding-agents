# Design Principles

This section captures the design principles used by this skill for manual review of Rust applications.

## A brief overview of common design principles

### SOLID

- Single Responsibility Principle (SRP): a type should own one responsibility; changes in one area of the domain should affect only one type.
- Open/Closed Principle (OCP): software should be open for extension and closed for modification.
- Liskov Substitution Principle (LSP): subtype values should be safely replaceable by callers without breaking behavior.
- Interface Segregation Principle (ISP): keep interfaces small and specific to each client need.
- Dependency Inversion Principle (DIP): depend on abstractions rather than concrete implementations.

### CRP (Composite Reuse Principle) / Composition over inheritance

Prefer composition with explicit behavior injection over inheritance-style extension.

### DRY (Don’t Repeat Yourself)

Each piece of knowledge should have one authoritative representation in the system.

### KISS

Keep designs as simple as possible; avoid avoidable complexity.

### Law of Demeter (LoD)

Expose behavior, not internals; assume minimal structure/knowledge about collaborators.

### Design by Contract (DbC)

Document and enforce preconditions, postconditions, and invariants at API boundaries.

### Encapsulation

Protect state and invariants by bundling data with behavior and controlling access to internals.

### Command-Query Separation (CQS)

Commands mutate state; queries read state. Avoid methods that do both in practice.

### Principle of Least Astonishment (POLA)

Default behavior should match reasonable user expectations and avoid surprising side effects.

### Linguistic Modular Units

Structure modules to align with language-level units and ownership boundaries.

### Self-Documentation

Prefer APIs that communicate intent directly through names, signatures, and contracts.

### Uniform Access

Expose capabilities through a consistent API style regardless of storage or computation.

### Single-Choice

Where alternatives are represented, centralize the authoritative list of choices.

### Persistence-Closure

When persisting objects, include enough related dependent state to keep reconstruction valid.
