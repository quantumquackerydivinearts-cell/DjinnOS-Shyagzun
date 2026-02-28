# Cobra + Shygazun Structural Spec (v0.1)

## Scope

This spec defines how Cobra scripts encode Shygazun lexical compounds using Python-style indentation.
It is a tooling-layer spec for parsing and placement emission. It does not grant semantic authority.

## Core Model

- Top-level Cobra lines define structural statements.
- Indented lines bind attributes to the immediately preceding top-level statement.
- Shygazun compounds are provided as opaque lexical payloads via `lex` (or aliases).

## Statement Form

```cobra
entity <id> <x> <y> <z> <tag>
```

Example:

```cobra
entity gate_01 12 8 portal
```

## Indented Attribute Form

Indented lines attach to the preceding statement:

```cobra
entity gate_01 12 8 portal
  lex TyKoWuVu
  state open
  layer foreground
```

Supported attribute formats:

- `key value`
- `key: value`

## Shygazun Lexical Attributes

The following keys are treated as Shygazun lexical fields:

- `lex`
- `akinenwun`
- `shygazun`

Example:

```cobra
entity actor_kael 4 3 actor
  lex TyKoWuVu
```

## Akinenwun Split Rule

Tooling split rule is structural:

- Regex tokenization: `[A-Z]+[a-z]*`
- Example: `TyKoWuVu` => `Ty | Ko | Wu | Vu`

No semantic inference is applied by this split.

## Emission Boundary

- Cobra source remains inert until explicit emission.
- `Emit Cobra Placements` performs structural emission through API placement calls.
- Kernel remains source of truth for events/frontiers.
- No direct CEG mutation from Cobra tooling.

## Non-Goals

- No quest/world inference.
- No implicit candidate selection.
- No auto-attestation.
- No semantic interpretation of Shygazun compounds.

## Validation Hints (Tooling)

Recommended lint warnings:

- `entity` line has fewer than 5 tokens.
- Indented line appears before any top-level statement.
- Empty value for `lex`/`akinenwun`/`shygazun`.
- Mixed tabs/spaces indentation.
