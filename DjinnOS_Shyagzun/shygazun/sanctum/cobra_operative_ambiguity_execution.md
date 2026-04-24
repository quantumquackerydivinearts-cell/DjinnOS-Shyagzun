# Kobra Execution Model: Operative Ambiguity
## First Principle Enshrinement Document — v0.1.0

---

## The Principle

> *An unresolved frontier in Kobra is not an error state awaiting correction.
> It is a valid operative condition in which coexisting candidate meanings
> execute in parallel until an external attestation collapses the frontier.
> The runtime does not choose. The witness chooses.*

---

## 1. Execution States

Kobra recognizes three fundamental execution states for any expression,
statement, or block:

```
Resolved       — frontier collapsed, single operative meaning, execution proceeds
Echoed         — hard parse failure, no corresponding output, input returned unchanged
FrontierOpen   — ambiguity unresolvable, both candidates live, execution bifurcates
```

These are not error levels. They are ontological states of the expression
within the Field. The runtime treats all three as valid and handles each
according to its own protocol.

---

## 2. The FrontierOpen Type

When the parser encounters an unresolvable ambiguity, it returns a typed
result rather than a failure flag:

```kobra
FrontierOpen(
    candidate_a: Expression,
    candidate_b: Expression,
    context:     ExecutionContext,
    witness:     WitnessSlot | None
)
```

- `candidate_a` and `candidate_b` are both fully formed operative expressions
- `context` carries the surrounding Field state at the moment of bifurcation
- `witness` is initially `None` — it becomes populated when an attestation arrives

A `FrontierOpen` is a **live object**. It is not suspended. Both candidates
are executing in parallel branches until the witness slot is filled.

---

## 3. Parallel Branch Execution

When a `FrontierOpen` is encountered at runtime, Kobra forks execution:

```
Expression E → FrontierOpen(A, B, ctx, None)
                    ├── Branch Alpha: execute A in ctx_a
                    └── Branch Beta:  execute B in ctx_b
```

Both branches:
- Operate on **copies** of the Field state at the bifurcation point
- May themselves produce further `FrontierOpen` states (nested bifurcation)
- Accumulate their own attestation requirements
- Cannot write to shared Field state until the frontier collapses

Branch results are held in a **Pending Field** — a temporary overlay on the
main Field that stores the outputs of both branches without committing either.

---

## 4. Attestation and Collapse

Collapse occurs when a witness fills the `WitnessSlot`:

```kobra
attest(frontier: FrontierOpen, choice: candidate_a | candidate_b, witness: Wand)
```

The attestation:
1. Verifies the witness has authority in the current Guild and role context
2. Records the attestation in the immutable history (DjinnOS Field)
3. Commits the chosen branch's Pending Field writes to the main Field
4. Discards the unchosen branch cleanly — no side effects escape
5. Returns the collapsed expression as a `Resolved` state

The witness **cannot** attest without a valid Wand credential. The Wand's
attestation chain is checked against the user's account, role, and Guild
registry before collapse is permitted.

---

## 5. Ambiguity as Instruction

In certain contexts, a `FrontierOpen` is not incidental — it is
**deliberately constructed** as an operative instruction. This is the
Cannabis Tongue's primary operative mode in Kobra.

A Cannabis Tongue compound appearing in executable position signals to
the runtime: *hold both, proceed with both, await witness*.

This is syntactically distinguished from accidental ambiguity by the
presence of a Cannabis Tongue marker in the expression. The runtime
does not treat these identically:

```
Accidental FrontierOpen  → flagged, witness requested, execution pauses
Deliberate FrontierOpen  → unmarked flag, execution bifurcates silently,
                           both branches live until natural attestation
```

The distinction matters for the Guild Hall — a deliberately ambiguous
message or contract is a different instrument than an accidentally
ambiguous one. Both require witnesses, but the deliberate form is
a **standing instrument** that can remain unresolved across sessions
until the right witness arrives.

---

## 6. Nested Bifurcation

A branch may itself produce a `FrontierOpen`. This creates a bifurcation
tree:

```
E → FrontierOpen(A, B)
        ├── A → FrontierOpen(A1, A2)
        │       ├── A1 → Resolved
        │       └── A2 → Resolved
        └── B → Resolved
```

Collapse is **depth-first from the leaves**. The outermost frontier cannot
collapse until all nested frontiers within the chosen branch have collapsed.

This means a complex Cannabis Tongue expression may require a **chain of
witnesses** — each collapsing one layer — before the full expression resolves.
This is not a limitation. This is the attestation chain functioning as
designed.

---

## 7. The Echo Protocol

Hard parse failures return the input unchanged:

```kobra
parse("unrecognized_token") → Echo("unrecognized_token", context, failure_type)
```

An `Echo` is also a live object. It:
- Carries the context of its failure
- Can be re-submitted to the parser after the dictionary has been extended
- Does not block surrounding execution — it floats in the Field as an
  unresolved placement until a Steward attests its meaning

This is consistent with the DjinnOS Field: *the Field never lies, it only
records*. An Echo is a recorded placement of unknown meaning, not a deletion.

---

## 8. Relationship to DjinnOS Kernel

Kobra's operative ambiguity model is a direct extension of DjinnOS core:

| DjinnOS Concept       | Kobra Expression         |
|-----------------------|--------------------------|
| Candidate             | FrontierOpen branch      |
| Frontier              | FrontierOpen state       |
| Attestation           | `attest()` with Wand     |
| Field placement       | Resolved or Echo object  |
| Immutable history     | Collapsed attestation log|
| Kernel honesty        | No silent collapse       |

The Kobra runtime **never collapses a frontier without a witness**.
Not for convenience. Not for performance. Not under any runtime condition.
This is the kernel's honesty guarantee expressed in executable form.

---

## 9. Summary of New Types

```kobra
type ExecutionState =
    | Resolved(value: Any, attestation: AttestationRecord)
    | Echo(input: Any, context: ExecutionContext, failure: FailureType)
    | FrontierOpen(
          candidate_a: Expression,
          candidate_b: Expression,
          context:     ExecutionContext,
          witness:     WitnessSlot | None,
          deliberate:  Bool
      )

type FailureType =
    | HardFailure       # no parse possible
    | UnknownToken      # token not in dictionary
    | ContextMissing    # parse possible but context insufficient

type WitnessSlot =
    | Empty
    | Filled(wand: Wand, timestamp: Timestamp, attestation_id: UUID)
```

---

## 10. Next Steps

This document establishes the execution model foundation.
The build order from here:

1. **Reverse Parser** — segment, identify, compose, hold frontiers,
   return typed results using these states
2. **Cannabis Tongue Byte Table** — formalize the deliberate ambiguity
   primitives and their byte addresses
3. **Communications and Server/Client Protocols** — Guild Hall messaging,
   wand-gated encryption, the Discord-analog distribution ecosystem

---

*Kobra Execution Model v0.1.0 — Operative Ambiguity First Principle*
*DjinnOS-Shygazun / quantumquackerydivinearts-cell*