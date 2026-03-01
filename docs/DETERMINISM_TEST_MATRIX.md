# Determinism and Frontier Conformance Test Matrix

## Scope
Contract-level test inventory for kernel/runtime behavior:
- replay determinism
- no premature collapse
- no deferred authority outside kernel/attestation flow

## T1-T12 Matrix

### T1 Canonical Candidate Hash
- Target: candidate hash generation.
- Input: identical candidate payload serialized with varied key order.
- Expectation: identical `candidate_hash`.
- Failure indicates: non-canonical hashing.

### T2 Eligibility Stores ID+Hash Only
- Target: eligibility event contract.
- Input: emit eligibility for candidate.
- Expectation: event contains `candidate_id`, `candidate_hash`; does not rely on mutable candidate snapshot for authority.
- Failure indicates: replay fragility due to mutable payload coupling.

### T3 Frontier Coexistence
- Target: frontier lifecycle.
- Input: two mutually undecided candidate paths.
- Expectation: both frontiers remain active until explicit retirement condition.
- Failure indicates: premature collapse.

### T4 Explicit Retirement Only
- Target: retirement logic.
- Input: frontier marked retired.
- Expectation: retirement contains explicit inconsistency/rule reason.
- Failure indicates: heuristic/implied collapse.

### T5 No Commit Without Attestation
- Target: commitment gate.
- Input: eligible candidate without witness attestation.
- Expectation: no irreversible commit; refusal/defer event emitted.
- Failure indicates: authority bypass.

### T6 Commit Requires Attested Transition
- Target: commitment path.
- Input: eligible candidate plus valid attestation.
- Expectation: commit occurs once with stable event lineage.
- Failure indicates: missing gate or duplicate commit.

### T7 Replay Determinism (Single Plan)
- Target: runtime replay.
- Input: fixed action/event sequence replayed twice.
- Expectation: identical terminal state hash and equivalent event stream.
- Failure indicates: hidden nondeterminism.

### T8 Replay Determinism (Cross-Process)
- Target: process/environment stability.
- Input: same replay on fresh process.
- Expectation: identical outputs to T7.
- Failure indicates: implicit environment dependency.

### T9 Ordering Freeze
- Target: canonical ordering contract.
- Input: shuffled frontiers/events with identical content.
- Expectation: deterministic sorted output (id asc / documented order).
- Failure indicates: unstable ordering.

### T10 Byte Table Boundary
- Target: symbol semantics boundary.
- Input: tokens with known byte IDs, unknown semantic context.
- Expectation: system preserves IDs/routing, does not infer semantic commitment.
- Failure indicates: meaning leakage from ID space.

### T11 Placement-First State Mutation
- Target: state update path.
- Input: query-only operations + non-placement action.
- Expectation: no world mutation unless explicit placement/action delta exists.
- Failure indicates: implicit mutation.

### T12 Attestation Auditability
- Target: audit chain.
- Input: commit flow with witness metadata.
- Expectation: witness id, attestation kind/tag, and target are traceable from commit lineage.
- Failure indicates: unverifiable authority chain.

## CI Recommendation
1. `conformance-fast`: T1, T2, T3, T5, T7, T9.
2. `conformance-full`: all tests including cross-process replay and audit trace tests.
3. Gate merges on:
   - replay mismatch
   - unattested commit
   - implicit frontier retirement

## Mapping To Existing Focus
- replay determinism: T1, T7, T8, T9.
- no premature collapse: T3, T4.
- no deferred authority outside kernel: T5, T6, T12.
