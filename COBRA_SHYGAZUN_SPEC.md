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

## Formula Capability Encryption (v2)

This section defines practical recipe security for dungeon-gated progression. It is additive to the structural grammar above.

### Goals

- Prevent recipe recovery unless dungeon requirements are met.
- Support partial order and nonviolent alternatives without weakening security.
- Keep enforcement server-authoritative.

### Security Model

- Treat `alchemical_formula_fragment` as flavor metadata only.
- Real recipe content is encrypted and never reconstructed client-side without server verification.
- Use authenticated encryption for all protected recipe payloads.

### Objects

- `recipe_id`: Stable recipe identifier.
- `recipe_ciphertext`: AEAD-encrypted recipe payload.
- `k_recipe`: Random symmetric recipe key (32 bytes).
- `share_i`: Shamir share of `k_recipe`.
- `unlock_policy`: Required dungeon clears, tier rules, and behavior constraints.
- `completion_claim`: Signed proof of a specific dungeon run outcome.
- `share_token`: Signed, audience-bound token granting one specific `share_i`.

### Provisioning Flow

1. Generate `k_recipe` with CSPRNG.
2. Encrypt canonical formula payload:
   - `recipe_ciphertext = AEAD_Encrypt(k_recipe, plaintext_formula, aad={recipe_id, version})`
3. Split `k_recipe` with Shamir `(k_of_n)`.
4. Bind each share to policy targets (dungeon, tier band, optional path constraints).
5. Store only:
   - `recipe_ciphertext`
   - share metadata and assignment
   - policy definition

### Dungeon Completion Claims

Server creates `completion_claim` after run finalization:

- `claim_id`, `actor_id`, `run_id`, `dungeon_id`, `difficulty_tier`
- `combat_kills`, `alerts_triggered`, `civilian_harm`
- `completion_mode` (`violent`, `mixed`, `pacifist`)
- `issued_at`, `expires_at`, `nonce`
- `sig` (server signature)

Claims are append-only and replay-protected by `claim_id` + `nonce`.

### Nonviolent Bonus Rule

Define pacifism score in `[0,1]`:

- `pacifism_score = 1 - weighted_normalized(combat_kills, alerts_triggered, civilian_harm)`

Policy can grant one of:

- Threshold reduction: `effective_k = k - 1` when `avg_pacifism_score >= threshold`.
- Wildcard credit: each qualifying pacifist clear grants `wildcard_share_credit += 1` up to max cap.

Do not issue raw shares as bonus. Issue policy-scoped bonus credits only.

### Share Release Policy

Server releases share material only when all are true:

- Claim signature valid.
- Claim belongs to requesting `actor_id`.
- Claim not expired and not replayed.
- Claim satisfies mapped policy for that share.
- Any anti-farm limits pass (cooldown, unique run lineage, or daily cap).

Returned object is `share_token`, not plaintext share by default.

### Reconstruction / Forge Flow

1. Client submits candidate `share_token`s for `recipe_id`.
2. Server verifies all tokens and policy bindings.
3. Server reconstructs `k_recipe` if valid shares meet `effective_k`.
4. Server decrypts `recipe_ciphertext`.
5. Server returns either:
   - decrypted recipe payload (trusted clients only), or
   - short-lived `forge_permit` (preferred).

### Recommended Crypto Primitives

- AEAD: `XChaCha20-Poly1305` or `AES-256-GCM`
- KDF (if deriving envelope keys): `HKDF-SHA256`
- Signatures: `Ed25519`
- Hashing / IDs: `SHA-256`

### Key Handling

- Keep long-lived signing keys in server KMS/HSM.
- Rotate key versions; include `key_version` in claims/tokens.
- Never embed master secrets in client builds.
- Zeroize transient plaintext key material where practical.

### Compatibility Policy

- No backward compatibility with legacy shard-only unlock behavior.
- Legacy fields (`textual_key_fragment`, `visual_key_fragment`, `shygazun_byte_sequence`, `alchemical_formula_fragment`) are not part of recipe authorization.
- Authorization is valid only when cryptographic claim and token verification succeeds under this v2 model.

### Canonical Payload Schemas

All timestamps are RFC3339 UTC strings. All IDs are lowercase ASCII tokens unless noted.

#### `completion_claim` (signed by server)

```json
{
  "claim_id": "clm_01jt6v8h8v9k3f3g3h2x4k7y5m",
  "workspace_id": "main",
  "actor_id": "player",
  "run_id": "run:sulphera_pride:14:97bb7965ff",
  "dungeon_id": "sulphera/pride",
  "difficulty_tier": 7,
  "combat_kills": 0,
  "alerts_triggered": 1,
  "civilian_harm": 0,
  "completion_mode": "pacifist",
  "pacifism_score": 0.93,
  "issued_at": "2026-03-04T21:42:00Z",
  "expires_at": "2026-03-11T21:42:00Z",
  "nonce": "n_5f78b7e677f14be4a0a445f3",
  "key_version": "sig-v2-2026q1",
  "sig_alg": "Ed25519",
  "sig": "base64url(signature_over_canonical_json_without_sig)"
}
```

Required fields:
- `claim_id`, `workspace_id`, `actor_id`, `run_id`, `dungeon_id`
- `difficulty_tier`, `combat_kills`, `alerts_triggered`, `civilian_harm`
- `completion_mode`, `pacifism_score`
- `issued_at`, `expires_at`, `nonce`, `key_version`, `sig_alg`, `sig`

#### `share_token` (issued after policy checks)

```json
{
  "token_id": "sht_01jt6vdc1z6x5sh9s3j9t0m9z8",
  "workspace_id": "main",
  "actor_id": "player",
  "recipe_id": "sulphuric_ink_v3",
  "share_ref": "share_4_of_8",
  "claim_id": "clm_01jt6v8h8v9k3f3g3h2x4k7y5m",
  "unlock_path": "dungeon_clear",
  "issued_at": "2026-03-04T21:43:00Z",
  "expires_at": "2026-03-05T21:43:00Z",
  "nonce": "n_50b790b31e2c4f9cb31f6ed3",
  "jti": "jti_01jt6ve18z6a1c1j8gm0xk5k3x",
  "key_version": "sig-v2-2026q1",
  "sig_alg": "Ed25519",
  "sig": "base64url(signature_over_canonical_json_without_sig)"
}
```

Required fields:
- `token_id`, `workspace_id`, `actor_id`, `recipe_id`, `share_ref`
- `claim_id`, `unlock_path`
- `issued_at`, `expires_at`, `nonce`, `jti`, `key_version`, `sig_alg`, `sig`

Notes:
- `share_ref` identifies server-held share material. Plain share bytes should not be embedded in client tokens.
- `unlock_path` enum: `dungeon_clear`, `pacifist_bonus`, `wildcard_credit`.

#### `forge_permit` (short-lived authorization)

```json
{
  "permit_id": "fgp_01jt6vg6z4tn5we5k8sw9n7t2e",
  "workspace_id": "main",
  "actor_id": "player",
  "recipe_id": "sulphuric_ink_v3",
  "effective_k": 4,
  "shares_used": [
    "share_1_of_8",
    "share_2_of_8",
    "share_4_of_8",
    "share_7_of_8"
  ],
  "issued_at": "2026-03-04T21:44:00Z",
  "expires_at": "2026-03-04T21:49:00Z",
  "nonce": "n_3298e0be1f7a4a50a53e02f4",
  "jti": "jti_01jt6vgk5r8m6q3kp83t12h7mw",
  "key_version": "sig-v2-2026q1",
  "sig_alg": "Ed25519",
  "sig": "base64url(signature_over_canonical_json_without_sig)"
}
```

Required fields:
- `permit_id`, `workspace_id`, `actor_id`, `recipe_id`
- `effective_k`, `shares_used`
- `issued_at`, `expires_at`, `nonce`, `jti`, `key_version`, `sig_alg`, `sig`

### Verification Checklist (Normative)

For `completion_claim`, `share_token`, and `forge_permit`, the verifier MUST:

1. Validate schema and required fields.
2. Reject if `expires_at` is in the past or `issued_at > now + allowed_clock_skew`.
3. Verify signature using `key_version` and `sig_alg`.
4. Enforce `workspace_id` and `actor_id` match caller/session.
5. Enforce one-time use via `claim_id`/`jti`/`nonce` replay tables.
6. Enforce policy binding (`dungeon_id`, tier, pacifism constraints, anti-farm limits).

If any check fails, authorization fails.

### JSON Schema (Draft 2020-12)

#### `completion_claim.schema.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://djinnos.local/schemas/completion_claim.schema.json",
  "title": "CompletionClaim",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "claim_id",
    "workspace_id",
    "actor_id",
    "run_id",
    "dungeon_id",
    "difficulty_tier",
    "combat_kills",
    "alerts_triggered",
    "civilian_harm",
    "completion_mode",
    "pacifism_score",
    "issued_at",
    "expires_at",
    "nonce",
    "key_version",
    "sig_alg",
    "sig"
  ],
  "properties": {
    "claim_id": { "type": "string", "pattern": "^clm_[a-z0-9]{20,}$" },
    "workspace_id": { "type": "string", "pattern": "^[a-z0-9_\\-]{1,64}$" },
    "actor_id": { "type": "string", "pattern": "^[a-z0-9_\\-]{1,64}$" },
    "run_id": { "type": "string", "minLength": 1, "maxLength": 256 },
    "dungeon_id": { "type": "string", "pattern": "^[a-z0-9_\\-]+/[a-z0-9_\\-]+$" },
    "difficulty_tier": { "type": "integer", "minimum": 1, "maximum": 20 },
    "combat_kills": { "type": "integer", "minimum": 0, "maximum": 1000000 },
    "alerts_triggered": { "type": "integer", "minimum": 0, "maximum": 1000000 },
    "civilian_harm": { "type": "integer", "minimum": 0, "maximum": 1000000 },
    "completion_mode": { "type": "string", "enum": ["violent", "mixed", "pacifist"] },
    "pacifism_score": { "type": "number", "minimum": 0, "maximum": 1 },
    "issued_at": { "type": "string", "format": "date-time" },
    "expires_at": { "type": "string", "format": "date-time" },
    "nonce": { "type": "string", "pattern": "^n_[A-Za-z0-9_\\-]{12,128}$" },
    "key_version": { "type": "string", "pattern": "^[A-Za-z0-9_.\\-]{1,64}$" },
    "sig_alg": { "type": "string", "enum": ["Ed25519"] },
    "sig": { "type": "string", "pattern": "^[A-Za-z0-9_\\-]{32,2048}$" }
  }
}
```

#### `share_token.schema.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://djinnos.local/schemas/share_token.schema.json",
  "title": "ShareToken",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "token_id",
    "workspace_id",
    "actor_id",
    "recipe_id",
    "share_ref",
    "claim_id",
    "unlock_path",
    "issued_at",
    "expires_at",
    "nonce",
    "jti",
    "key_version",
    "sig_alg",
    "sig"
  ],
  "properties": {
    "token_id": { "type": "string", "pattern": "^sht_[a-z0-9]{20,}$" },
    "workspace_id": { "type": "string", "pattern": "^[a-z0-9_\\-]{1,64}$" },
    "actor_id": { "type": "string", "pattern": "^[a-z0-9_\\-]{1,64}$" },
    "recipe_id": { "type": "string", "pattern": "^[a-z0-9_\\-]{1,128}$" },
    "share_ref": { "type": "string", "pattern": "^share_[0-9]+_of_[0-9]+$" },
    "claim_id": { "type": "string", "pattern": "^clm_[a-z0-9]{20,}$" },
    "unlock_path": { "type": "string", "enum": ["dungeon_clear", "pacifist_bonus", "wildcard_credit"] },
    "issued_at": { "type": "string", "format": "date-time" },
    "expires_at": { "type": "string", "format": "date-time" },
    "nonce": { "type": "string", "pattern": "^n_[A-Za-z0-9_\\-]{12,128}$" },
    "jti": { "type": "string", "pattern": "^jti_[a-z0-9]{20,}$" },
    "key_version": { "type": "string", "pattern": "^[A-Za-z0-9_.\\-]{1,64}$" },
    "sig_alg": { "type": "string", "enum": ["Ed25519"] },
    "sig": { "type": "string", "pattern": "^[A-Za-z0-9_\\-]{32,2048}$" }
  }
}
```

#### `forge_permit.schema.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://djinnos.local/schemas/forge_permit.schema.json",
  "title": "ForgePermit",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "permit_id",
    "workspace_id",
    "actor_id",
    "recipe_id",
    "effective_k",
    "shares_used",
    "issued_at",
    "expires_at",
    "nonce",
    "jti",
    "key_version",
    "sig_alg",
    "sig"
  ],
  "properties": {
    "permit_id": { "type": "string", "pattern": "^fgp_[a-z0-9]{20,}$" },
    "workspace_id": { "type": "string", "pattern": "^[a-z0-9_\\-]{1,64}$" },
    "actor_id": { "type": "string", "pattern": "^[a-z0-9_\\-]{1,64}$" },
    "recipe_id": { "type": "string", "pattern": "^[a-z0-9_\\-]{1,128}$" },
    "effective_k": { "type": "integer", "minimum": 1, "maximum": 64 },
    "shares_used": {
      "type": "array",
      "minItems": 1,
      "maxItems": 64,
      "uniqueItems": true,
      "items": { "type": "string", "pattern": "^share_[0-9]+_of_[0-9]+$" }
    },
    "issued_at": { "type": "string", "format": "date-time" },
    "expires_at": { "type": "string", "format": "date-time" },
    "nonce": { "type": "string", "pattern": "^n_[A-Za-z0-9_\\-]{12,128}$" },
    "jti": { "type": "string", "pattern": "^jti_[a-z0-9]{20,}$" },
    "key_version": { "type": "string", "pattern": "^[A-Za-z0-9_.\\-]{1,64}$" },
    "sig_alg": { "type": "string", "enum": ["Ed25519"] },
    "sig": { "type": "string", "pattern": "^[A-Za-z0-9_\\-]{32,2048}$" }
  }
}
```

Canonical repository locations:
- `schemas/shygazun_crypto/completion_claim.schema.json`
- `schemas/shygazun_crypto/share_token.schema.json`
- `schemas/shygazun_crypto/forge_permit.schema.json`

Validation command:
- `python scripts/validate_shygazun_crypto_schemas.py`
- Optional payload checks:
  - `python scripts/validate_shygazun_crypto_schemas.py --completion-claim <path> --share-token <path> --forge-permit <path>`
