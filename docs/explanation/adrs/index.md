# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records (ADRs) documenting significant architectural and design decisions made for the Keycloak infrastructure-as-code implementation.

## About ADRs

ADRs are documents that capture important architectural decisions along with their context and consequences. They help teams understand:

- **Why** decisions were made
- **What** forces influenced the decisions
- **What** the consequences are (positive and negative)
- **When** decisions were made and by whom

ADRs are immutable records. If a decision changes, we create a new ADR that supersedes the old one rather than modifying the original.

## ADR Index

| ADR                                            | Title                                                 | Status   | Date       |
| ---------------------------------------------- | ----------------------------------------------------- | -------- | ---------- |
| [0001](0001-keycloak-security-architecture.md) | Keycloak Security Architecture and IaC Best Practices | Accepted | 2026-02-25 |

## ADR Template

When creating new ADRs, use the following structure:

```markdown
# ADR-NNNN: Title

**Status:** [Proposed | Accepted | Deprecated | Superseded]  
**Date:** YYYY-MM-DD  
**Deciders:** [Who was involved]

## Context

What forces are at play? What's the situation that requires a decision?

## Decision

What is the change that we're proposing/accepting?

## Consequences

What becomes easier or harder after this decision?

### Positive

### Negative

### Neutral

## References

Links to supporting material.

## Related ADRs

Links to related decisions.
```

## Status Definitions

- **Proposed**: Under discussion, not yet approved
- **Accepted**: Decision has been made and is currently in effect
- **Deprecated**: No longer relevant but left for historical context
- **Superseded**: Replaced by another ADR (link to the new one)

## Contributing

When making significant architectural decisions:

1. Create a new ADR in this directory
2. Use the next sequential number (e.g., 0002, 0003)
3. Follow the template structure above
4. Update this index with your new ADR
5. Include the ADR in your pull request along with the implementation

## References

- [Diataxis Framework - Explanation](https://diataxis.fr/explanation/) (this is explanation-oriented documentation)
- [ADR GitHub Organization](https://adr.github.io/)
- [Michael Nygard's ADR article](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
