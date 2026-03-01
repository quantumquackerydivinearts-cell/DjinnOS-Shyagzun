# Math Boundary Contract

## Purpose
Define the allowed role of math in DjinnOS runtime, kernel, and tooling so semantics remain externally attested and replay-safe.

## Core Boundary
1. Numeric/state math is allowed for hosted phenomena:
   - tension, relaxation, cost, obligation, pressure, growth, decay, thresholds.
2. Numeric/state math is not allowed to claim semantic ownership:
   - no token-to-meaning authority from arithmetic.
   - no "recognized Lotus" claim from internal computation.

## Runtime Semantics Rules
1. Placement-first:
   - state changes are driven by explicit placements/actions.
   - no implicit semantic mutation.
2. Completion is commitment-bound:
   - irreversible effects require witnessed/attested commit.
   - no commit from eligibility alone.
3. Ambiguity is first-class:
   - frontiers may coexist.
   - no auto-collapse.
4. External primacy:
   - Lotus is outside executable inference and cannot be implemented as a rule engine.

## Causal/Event Model Rules
1. Append-only events:
   - events are never rewritten.
2. Candidate indirection:
   - eligibility records `candidate_id` + `candidate_hash`.
   - do not store mutable candidate payload as authority.
3. Deterministic ordering:
   - canonical sorting and hashing are frozen contracts.
   - replay must produce equivalent outcomes from identical inputs.
4. Frontier retirement:
   - requires explicit inconsistency proof or declared rule violation.
   - never retire by heuristic convenience.

## Byte Table Boundary
1. Byte table is a finite symbol/basis ID space for routing and audit.
2. Byte table is not semantic truth.
3. Any semantic interpretation must pass through explicit runtime policies and attestable transitions.

## Geometry/Rendering Math Guidance
1. For 3D interaction, noncommutative transforms are acceptable and expected.
2. Exotic scalars are allowed only as explicit weighting/encoding terms.
3. Rendering math cannot bypass semantic lifecycle constraints.

## Red Lines
1. No AST-first semantic authority.
2. No Lotus-as-plugin, Lotus-as-rules, or Lotus-as-cost-curves.
3. No automatic frontier collapse.
4. No commitment without external attestation.

## Acceptance Criteria
1. Replay determinism holds under fixed canonical ordering/hashing.
2. Eligibility does not imply commitment.
3. Frontier coexistence is preserved until explicit closure condition.
4. All irreversible transitions are externally attestable.
