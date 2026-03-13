DjinnOS Filesystem Abstraction
Corpus-Oriented Storage Model (v0)
Purpose

This document describes the filesystem abstraction used by DjinnOS-aligned systems.

The filesystem is treated not as a neutral container, but as a semantic boundary that makes:

risk explicit,

persistence intentional,

and movement accountable.

The goal is not security by obscurity, but legibility by structure.

Core Principle

Where something lives determines what may be done with it.

The filesystem encodes:

degrees of persistence,

exposure expectations,

and acceptable transformations.

This reduces reliance on policy enforcement and increases mechanical honesty.

The Corpus Model

DjinnOS uses a Corpus-oriented filesystem model.

Corpus refers to anything that has embodiment in any dimension —
data, artifacts, systems, or processes.

Each corpus degree corresponds to a directory class with strict intent.

Canonical Root

All DjinnOS-aligned work exists under a single root:

/djinnos


Nothing outside this root is assumed to be governed.

Directory Classes (Corpus Degrees)
1. sanctum/ — Authoritative (Zot)

Intent:
Long-lived truth and authority.

Typical contents:

contracts

licenses

canonical specifications

cryptographic material

governance artifacts

Rules:

changes are deliberate and rare

no transient tooling

no automated sync by default

edits imply responsibility

If data here is altered, the system’s meaning changes.

2. atelier/ — Creative / Adaptive (Mel)

Intent:
Exploration, construction, learning.

Typical contents:

drafts

source code

design notes

experiments

unreleased assets

Rules:

iteration is expected

mistakes are permitted

promotion is explicit

nothing is assumed final

This is the default working space.

3. conduit/ — Transmissive (Puf)

Intent:
Outbound material and exposure.

Typical contents:

exports

builds

client deliverables

published artifacts

communication payloads

Rules:

nothing originates here

everything here is assumed observable

contents are reproducible

secrets do not belong here

Movement into conduit is a statement of intent.

4. crucible/ — Volatile / Dangerous (Shak)

Intent:
Containment of risk.

Typical contents:

installers

untrusted binaries

reverse engineering work

destructive tests

temporary scripts

Rules:

persistence is discouraged

credentials are forbidden

periodic wiping is expected

no authority flows outward

Crucible exists so danger has a place.

5. kael/ — System Clusters (Kael)

Intent:
Embodied systems and long-lived environments.

Typical contents:

virtual machines

containers

engines

language runtimes

toolchains

Rules:

each subdirectory is a system boundary

interfaces must be documented

assumptions must be explicit

no silent coupling

Kael is where worlds live, not files.

Movement Semantics

Movement between directories is semantically meaningful.

Allowed (explicit):

atelier → conduit (publishing)

crucible → atelier (after review)

atelier → sanctum (canonization)

Discouraged:

sanctum → conduit

crucible → sanctum

Forbidden:

conduit → anywhere

Once something is transmissive, it is no longer authoritative.

Operational Posture (Contextual)

While DjinnOS itself is posture-agnostic, this filesystem pairs naturally with operational postures:

Sealed — work confined to sanctum / atelier

Working — atelier + selected systems

Outward — conduit-facing activity

Posture is inferred from location, not toggles.

What This Model Does Not Do

This filesystem abstraction does not:

enforce access control by itself

prevent all leakage

replace OS permissions

guarantee confidentiality

It provides structural clarity, not magical protection.

Why This Matters

Most systems fail because:

everything is treated as equally persistent,

exposure is accidental,

and responsibility is diffuse.

This model ensures:

risk is spatially visible,

responsibility is locatable,

and mistakes are legible.

Auditors can see intent.
Collaborators can understand boundaries.
Operators can reason while tired.

Status

Version: v0.1.1

Scope: Single-machine abstraction

Enforcement: Conventional filesystem + discipline

Evolution: Incremental

The abstraction is stable.
Implementations may vary.

Final Note

If you are unsure where something belongs:

Put it in atelier.

If you are unsure whether something should be shared:

It does not belong in conduit.

The filesystem exists to answer these questions before mistakes happen.