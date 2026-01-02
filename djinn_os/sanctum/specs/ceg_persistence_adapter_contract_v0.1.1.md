CEG Persistence Adapter Contract (v0.1.0)
Status

Draft → Intended to Freeze

This document defines the sole allowed interface between the Shygazun Kernel’s Canonical Event Graph (CEG) and any persistence mechanism.

This contract is structural only.
It introduces no semantics, no authority, and no interpretation.

1. Purpose

The CEG Persistence Adapter exists to:

Persist kernel-emitted events and edges

Restore them verbatim

Preserve ordering and determinism

Enable replay without inference

It does not:

Validate events

Modify events

Infer meaning

Enforce policy

Optimize storage

Collapse or summarize history

2. Core Invariants (Frozen)

A compliant adapter MUST satisfy all of the following:

Append-only

No deletion

No mutation

No reordering

Lossless

Stored data must round-trip bit-equivalent at the JSON level

Order-preserving

Events are returned in the exact order received

Edges are returned in the exact order received

Kernel-agnostic

Adapter must not depend on kernel internals

Adapter must accept plain mappings (Mapping[str, Any])

Filesystem-agnostic

Adapter must not derive meaning from paths, filenames, or directories

3. Data Model
3.1 Event Shape

The adapter treats all events opaquely.

Minimum required keys (not enforced, but assumed by kernel tooling):

{
  "id": "string",
  "kind": "string",
  "at": { "tick": number, "causal_epoch": string }
}


The adapter MUST NOT:

Require these keys

Enforce schemas

Reject unknown fields

3.2 Edge Shape

Edges are treated as nominal structures defined elsewhere.

The adapter MUST store and return them verbatim.

4. Adapter Interface
4.1 Required Interface (Python)
class CEGPersistenceAdapter(Protocol):

    def append_event(self, event: Mapping[str, Any]) -> None:
        ...

    def append_edge(self, edge: Edge) -> None:
        ...

    def load_events(self) -> Sequence[Mapping[str, Any]]:
        ...

    def load_edges(self) -> Sequence[Edge]:
        ...

4.2 Behavioral Guarantees

append_* MUST be synchronous

load_* MUST return data in append order

Duplicate IDs are allowed (kernel handles meaning)

Adapter MUST NOT deduplicate

5. Error Handling

Adapters MUST fail loudly and immediately on:

Write failures

Corrupt reads

Partial writes

Permission errors

Adapters MUST NOT:

Retry silently

Auto-repair

Invent defaults

Drop records

6. Reference Implementations (Non-Normative)
6.1 JSONL Adapter (Recommended v0)

One event per line

One edge per line

Separate files

UTF-8 only

No compression

This is the baseline sanity implementation.

6.2 SQLite Adapter (Optional Later)

Single table for events

Single table for edges

No indexes except autoincrement

No migrations without version bump

7. Explicit Non-Goals

This adapter does NOT:

Support queries

Support partial loads

Support filtering

Support schema evolution

Support branching timelines

Those are layer violations.

8. Relationship to Kernel

Kernel emits → adapter stores

Adapter returns → kernel replays

No callbacks

No hooks

No interpretation

The adapter never speaks first.

9. Freeze Criteria

This document may be frozen when:

JSONL adapter passes conformance replay test

Kernel can reboot and replay without divergence

No adapter code references kernel internals

Once frozen, changes require:

Version bump

Explicit justification

Replay compatibility statement

10. Canonical Statement

The persistence adapter remembers everything
and understands nothing.