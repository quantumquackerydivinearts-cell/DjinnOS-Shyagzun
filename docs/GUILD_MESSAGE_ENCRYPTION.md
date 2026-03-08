**Guild Message Encryption**

Purpose:
- derive guild message envelopes from wand identity plus tri-sourced entropy
- bind Guild Hall messaging to physical artifact provenance and current attestation state

Current scope:
- endpoint: `POST /v1/guild/messages/encrypt`
- service emits a message envelope with:
  - `schema_family = guild_message_envelope`
  - `schema_version = v1`
  - `cipher_family = experimental_hash_stream_v1`

Tri-source derivation inputs:
- `system_entropy_digest`
- `temple_entropy_digest`
- `theatre_entropy_digest`
- `wand_digest`
- `attestation_media_digests`
- `context_digest`

Important constraint:
- current cipher family is experimental and exists to establish the service boundary, envelope shape, and derivation lineage
- do not treat `experimental_hash_stream_v1` as final production cryptography

Related schema:
- `schemas/guild_message_envelope.schema.json`

Desktop surfaces:
- `Guild Hall`
  - derivation inputs
  - wand id
  - temple/theatre digests
  - attestation media digests
- `Messages`
  - message draft
  - envelope generation action

Relationship to wand damage attestation:
- validated wand damage media digests can be copied directly into guild message derivation
- this allows damage attestation state to influence later message key epochs without mutating provenance
