# Shygazun Kernel Conformance Runner — Minimal Specification (v0.1.1)

This document defines the **minimum required semantics** for a conformance
test runner capable of executing `conformance.json` for the Shygazun Kernel.

The runner is an **external verifier**.  
It must not interpret meaning, infer intent, or optimize execution order.

---

## 1. Scope and Guarantees

A compliant runner MUST:

- Execute tests strictly in the order defined
- Preserve and substitute variables deterministically
- Perform HTTP calls as specified
- Evaluate assertions mechanically
- Compute canonical JSON hashes exactly as specified
- Respect pending tests without failing the run

A compliant runner MUST NOT:

- Reorder test steps
- Skip required tests
- Normalize or “clean up” kernel output
- Infer semantics from field contents
- Collapse multiple failures into one

---

## 2. Execution Model

### 2.1 Test Order

- Tests are executed in the order they appear.
- Steps within a test are executed sequentially.
- Variables saved in earlier steps are available to later steps.

### 2.2 Test Status

Each test has a `status`:

- `required` → failure fails the entire run
- `pending` → skipped, reported as pending, never fails the run

---

## 3. Variable Substitution

### 3.1 Variable Syntax

Variables are referenced using double braces:

{{field_id}}
{{candidate_to_commit}}

### 3.2 Substitution Rules

- Substitution occurs **before** the HTTP call is made.
- If a variable is `null` at substitution time, it must be replaced with JSON `null`.
- Missing variables are a runner error.

---

## 4. HTTP Call Semantics

### 4.1 Call Object

Each step with a `call` MUST perform:

- HTTP method
- Path (with variable substitution)
- Optional JSON body
- Expect `application/json` response

### 4.2 Error Handling

- Non-2xx responses fail the step unless explicitly asserted
- Transport errors fail the test immediately

---

## 5. Save Semantics

### 5.1 Direct Save

Example:
```json
"save": {
  "field_id": "$.field_id"
}
JSONPath is evaluated against the response body

The extracted value is stored verbatim

5.2 Canonical Hash Save
Example:

json
Copy code
"save": {
  "field_hash_1": {
    "canonical_hash": "$.field",
    "exclude_metadata_keys_from": "{{diff_exempt_metadata_keys}}"
  }
}
Process:

Extract JSON value at path

Remove exempt metadata keys (see §6.3)

Canonicalize JSON (see §6)

Hash result

Store hash string

6. Canonical JSON Rules
6.1 Canonicalization
Canonical JSON is defined as:

UTF-8 encoding

Object keys sorted lexicographically

Arrays kept in kernel-defined order

No whitespace

Numbers unmodified (no rounding)

6.2 Required Array Orders
Runner MUST assume kernel already emits arrays in canonical order:

frontiers: id ascending

ceg.events: tick asc → kind asc → id asc

ceg.edges: from asc → to asc → type asc

Runner MUST NOT reorder arrays.

6.3 Metadata Exemption
exclude_metadata_keys_from applies ONLY to:

objects named metadata

Rules:

Remove only keys listed

Do not remove other keys

Do not remove attestation payload data

Do not remove semantic fields

7. Assertion Semantics
Assertions are evaluated after the call completes.

7.1 Assertion Types
http_status
Passes if HTTP status equals value.

equals
Path value must equal value.

not_equals
Path value must not equal value.

exists
Path must resolve to at least one value.

contains
Array at path must contain value.

not_contains
Array at path must not contain value.

contains_any
Array must contain at least one of the listed values.

count_equals
Number of items at path equals value.

count_gte
Number of items at path ≥ value.

all
All values at path must satisfy predicate.

for_each
For each item at path, run nested assertions.

equals_subset_except
Compare current JSON object to saved snapshot:

Objects must be identical

Differences allowed only under explicitly listed top-level keys

8. Repeat Semantics
Steps with:

json
Copy code
"repeat": N
MUST be executed N times sequentially.
Assertions apply to each execution.

9. Pending Tests
For tests with status: "pending":

Steps MUST NOT execute

Test MUST be reported as pending

Pending tests MUST NOT affect pass/fail outcome

10. Failure Semantics
A failure MUST include:

Test ID

Step ID

Assertion type

JSONPath

Expected vs actual value

Runner MUST continue executing remaining tests unless configured otherwise.

11. Output Requirements
Runner MUST produce:

Per-test pass/fail/pending status

Failure diagnostics

Stored variable table (final values)

Canonical hash values used in comparisons

Human-readable and machine-readable output formats are both acceptable.

12. Non-Goals (Explicit)
The runner does NOT:

Interpret Shygazun

Understand candidates or frontiers

Enforce metaphysics

Optimize kernel behavior

It verifies structural honesty only.

13. Compliance Statement
A runner is Shygazun Conformance Compatible if and only if:

It implements all rules in this document

It passes the full conformance pack without modification

It does not add interpretation beyond what is specified here

---