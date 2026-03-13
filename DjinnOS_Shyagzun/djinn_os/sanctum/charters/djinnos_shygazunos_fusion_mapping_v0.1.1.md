Revised Charter → Code → Filesystem Mapping (v0.1.1)
0. “DjinnOS is not an operating system” (revised, precise)

Charter

DjinnOS is not an operating system.

Clarification (important)
DjinnOS does not replace the host OS kernel, scheduler, or permissions.
However, ShygazunOS provides a semantic filesystem abstraction that DjinnOS respects.

So the corrected statement is:

DjinnOS is not a general-purpose OS, but it may inhabit a semantically structured filesystem.

Code impact

No POSIX abstractions in kernel

Filesystem semantics live outside kernel logic

1. “Where something lives determines what may be done with it”

Filesystem Charter

Where something lives determines what may be done with it.

Code mapping

Kernel accepts file references as opaque

IDE and tooling enforce placement discipline

Promotion between corpus degrees is explicit and reviewable

Never allowed

Kernel logic branching on filesystem path

Implicit authority inferred from location

2. The Corpus Root

Filesystem

/djinnos


Repo mapping

djinnos/
├── sanctum/
├── atelier/
├── conduit/
├── crucible/
└── kael/


Everything we discussed earlier now lives inside atelier/ by default.

3. Corpus Degrees → Repo Structure
3.1 sanctum/ — Authoritative (Zot)

Intent
Canonical truth, meaning-bearing artifacts.

Repo mapping

djinnos/sanctum/
├── charters/
│   ├── djinnos_charter_v0.1.1.md
│   ├── shygazunos_filesystem_v0.1.1.md
│   └── charter_code_mapping_v0.1.1.md
│
├── specs/
│   ├── kernel_api_v0.1.1.md
│   ├── ide_api_v0.1.1.md
│   └── conformance_spec_v0.1.1.md
│
└── governance/
    ├── version_policy.md
    └── attestation_policy.md


Rules (enforced socially + procedurally)

Changes require:

version bump

explicit commit message

often a witness (human, not kernel)

CI may block changes here without approval

Kernel relationship

Kernel behavior must conform to sanctum

Sanctum never imports kernel code

3.2 atelier/ — Creative / Adaptive (Mel)

Intent
Where almost all work happens.

Repo mapping

djinnos/atelier/
├── kernel/
├── ide/
├── conformance/
├── docs/
├── experiments/
└── notes/


This is where everything we’ve built so far belongs.

Rules

Iteration encouraged

Breaking things is acceptable

Promotion is explicit

Key invariant

Nothing in atelier is assumed canonical.

3.3 conduit/ — Transmissive (Puf)

Intent
Outbound, observable artifacts.

Repo mapping

djinnos/conduit/
├── releases/
│   ├── djinnos_v0.1.1.tar.gz
│   └── checksums/
├── published_specs/
└── demos/


Rules

Nothing originates here

Everything here must be reproducible from atelier

Secrets are forbidden

Critical invariant

Once something enters conduit, it may never regain authority.

This mirrors your conformance philosophy perfectly.

3.4 crucible/ — Volatile / Dangerous (Shak)

Intent
Containment of risk.

Repo mapping

djinnos/crucible/
├── fuzzing/
├── untrusted_inputs/
├── reverse_engineering/
└── destructive_tests/


Rules

Wiped regularly

No credentials

No sanctum imports

Kernel relationship

Crucible may attack the kernel

Kernel must survive or fail honestly

This is where adversarial testing lives.

3.5 kael/ — System Clusters (Kael)

Intent
Embodied systems, not files.

Repo mapping

djinnos/kael/
├── djinnos_runtime/
│   ├── containers/
│   ├── vms/
│   └── orchestration/
├── shygazun_engines/
└── toolchains/


Rules

Each subdir is a world boundary

Interfaces documented

No silent coupling

Important
Kael is where DjinnOS instances run, not where they are defined.

4. Movement Semantics → Development Workflow
Movement	Meaning	Tooling
atelier → sanctum	Canonization	Review + version bump
atelier → conduit	Publication	Build + checksum
crucible → atelier	Salvage	Explicit copy + annotation
conduit → anywhere	❌ Forbidden	CI / human enforcement

This replaces many policies with spatial clarity.

5. How Kernel + Filesystem Interact (carefully)
Allowed

IDE warns based on location
(“You are editing sanctum material.”)

CI enforces rules by path

Humans reason about risk spatially

Forbidden

Kernel branching on filesystem path

Filesystem implying semantic authority to kernel

“Sanctum mode” flags inside runtime

Key sentence to freeze

Filesystem location may constrain human and tooling behavior,
but never kernel semantics.

6. Updated “Safety Model” Mapping

Charter

DjinnOS assumes the world is hostile by default.

Now enforced by

Kernel invariants (witness, refusal, history)

Filesystem corpus separation (risk visibility)

Crucible containment

This is defense in depth without magic.