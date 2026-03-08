**Entropy Source Provenance**

Purpose:
- version the non-system entropy records mixed into guild message and wand epoch derivation
- distinguish temple/garden provenance from theatre/performance provenance

Contracts:
- `schemas/temple_entropy_source.schema.json`
- `schemas/theatre_entropy_source.schema.json`

Temple source requirements:
- `schema_family = temple_entropy_source`
- `schema_version = v1`
- `provenance_id`
- `source_type`
- `state_digest`

Theatre source requirements:
- `schema_family = theatre_entropy_source`
- `schema_version = v1`
- `provenance_id`
- `source_type`
- `media_digest`

Operational rules:
- empty source payloads are ignored
- non-empty source payloads must satisfy the versioned contract
- source records are hashed into the entropy mix when present
- original source records are carried forward in the returned derivation lineage

Security note:
- these records enrich derivation context; they do not replace OS entropy
- wand revocation remains enforced separately through the latest epoch state
