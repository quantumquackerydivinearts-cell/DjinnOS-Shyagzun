External Adopter Guide — Shygazun Kernel v0.1.1
How to integrate without breaking honesty

This guide is for anyone embedding or extending the Shygazun Kernel.
It defines what you may do, what you must not do, and how to prove you didn’t.

The kernel is an honesty machine:

it records events

it refuses when it cannot proceed

it never infers meaning

it never smuggles authority

If you want “smart behavior,” build it outside the kernel and feed it back only as structural facts.

1) Integration Contract
You may:

host the kernel inside any runtime (FastAPI, CLI, Electron, VM, container)

store its event graph anywhere (disk, DB, object store)

build UI/IDE/agent layers around it

run arbitrary analysis on outputs

replay bundles externally

You must not:

alter kernel behavior based on file paths, mount points, storage backend, OS user, environment variables, or UI state

reorder kernel steps

delete or mutate kernel history

infer meaning from event placement or storage location

add “helpful” normalization that changes hashes, ordering, or representation

2) What counts as “breaking the kernel”

You broke the kernel if any of these become true:

A. Path-based authority

Kernel execution differs based on:

filesystem location

repo folder (sanctum/atelier/etc.)

mount context

storage backend (sqlite vs memory vs s3)

environment toggles (“production mode”)

user identity in the host OS

Rule: tooling may enforce discipline by path; kernel may not.

B. Silent semantic inference

Kernel begins to:

interpret fields like “utterance,” “tag,” “payload,” “candidate_id”

“help” resolve ambiguity

choose winners

suppress candidates

auto-commit or auto-attest

apply heuristics

Rule: kernel records, refuses, or waits. It does not decide.

C. History rewriting

If you:

remove events

collapse events

merge events

“dedupe” events

adjust timestamps/ticks retroactively

change event IDs for convenience

Rule: append-only means append-only.

D. Determinism break

Same input bundle produces different canonical output (hash mismatch).

Common causes:

unordered dict iteration

non-canonical JSON serialization

sorting arrays “helpfully”

time-based IDs

random IDs

different ordering of register outputs

Rule: determinism is not optional; it’s the point.

3) Allowed Extensions (safe patterns)
Pattern 1 — External Meaning Engines (recommended)

You can build engines that:

interpret events

propose actions

generate candidates

recommend resolutions

But they must do so outside the kernel.

They may output:

candidate proposals (via registers)

attestations (recorded as events)

placements (new utterances)

They must not:

patch kernel internals

modify kernel history

inject hidden state

Pattern 2 — Projections (runtime/UI state)

You may maintain a derived “projection” layer:

UI layout

human-readable summaries

dashboards

search indices

caches

Projections must be:

disposable

regenerable from event history

non-authoritative

Pattern 3 — Persistence adapters

You may persist:

full event list

full edge list

field snapshots (if you have them)

replay bundles

But:

loading must be faithful

storage format must not alter order or values

canonical hashes must remain stable

4) Register Plugin Rules (do’s and don’ts)

Registers are where “intelligence” tries to creep in. Keep them honest.

Registers may:

admit fragments (structurally)

propose candidates

declare explicit forbids_candidates

declare lotus requirements

constrain candidate sets (structurally)

Registers must not:

look at filesystem paths

look at network state

look at timestamps outside kernel clock

use randomness

depend on host machine identity

infer meaning from “where” a file lives

Determinism requirement

Given the same field history and same inputs:

propose() must return candidates in a deterministic order

conflicts must be explicit, not inferred

lotus must be declared, not guessed

If a register needs nondeterminism, it belongs in crucible/ as an experiment, not in production.

5) Attestations: facts, not actions

Attestation events are:

recorded facts

opaque payloads

optional targets

They must not:

auto-trigger commitments

auto-resolve lotus internally

auto-create edges

change eligibility

If you want an attestation to mean something, write an external meaning engine that:

reads the event graph

proposes a new placement or candidate

optionally requests a commit through an explicit API call

6) Canonicalization & Hashing
Required invariants

object keys sorted

arrays not reordered by runner/tooling

no whitespace differences affecting hashes

stable event IDs (hash-derived, not time-derived)

Never do this

pretty-print JSON before hashing

“normalize” numbers

reorder arrays “for readability”

drop metadata keys unless explicitly exempted by conformance rules

7) Minimal Compliance Checklist (adopter self-test)

An integration is “Kernel Compatible” if:

 Kernel does not read filesystem path for semantics

 Kernel does not change behavior based on mount/backend

 All events are append-only

 Event IDs are deterministic

 Register outputs are deterministic

 Arrays are not reordered by tooling

 Same replay bundle → same canonical hash

 Attestations are recorded but not resolved internally

 Any “meaning” lives outside kernel and is explicit

If any checkbox fails, the integration is non-compliant.

8) Recommended integration architecture

Adopter stack:

Kernel (authoritative causality)

CEG store (append-only log)

Projection layer (UI/search summaries)

Meaning engines (optional, external, replaceable)

Conformance runner (tests honesty)

Rule of thumb:
If you can delete a component and regenerate it from the CEG, it’s safe to keep outside the kernel.

9) What to do when you want to add features

If you want to add:

commitments

lotus resolution

witness gating

negotiation loops

arbitration rules

Do it as:

a new event type (recorded)

a new external engine (interprets)

conformance tests (prove no authority leakage)

only then, a kernel extension (if absolutely required)

Most features never need to enter the kernel.

10) Compatibility statement

An adopter is Shygazun Kernel Compatible if and only if:

they preserve frozen v0.1.1 invariants

they pass the conformance pack without modifying it

they add no implicit authority or interpretation

they maintain determinism under replay