**Wand Damage Attestation**

Purpose:
- record multimedia proof that a physical wand artifact has changed condition
- preserve the original image evidence as authoritative source material
- allow downstream key-epoch scrambling without mutating wand provenance

Authority split:
- provenance remains append-only historical truth
- damage attestation records mutable condition evidence
- key epochs change after attested damage, not by rewriting provenance

Schema:
- `schemas/wand_damage_attestation.schema.json`

Required fields:
- `schema_family = "wand_damage_attestation"`
- `schema_version = "v1"`
- `wand_id`
- `notifier_id`
- `damage_state`
- `media[]`

Damage states:
- `worn`
- `chipped`
- `cracked`
- `broken`
- `restored`
- `retired`

Allowed image MIME types:
- `image/heic`
- `image/heif`
- `image/jpeg`
- `image/png`
- `image/webp`

Allowed file extensions:
- `.heic`
- `.heif`
- `.jpg`
- `.jpeg`
- `.png`
- `.webp`

Evidence rules:
- original HEIC/HEIF is accepted as authoritative evidence
- conversion to JPEG/PNG is optional and secondary
- if transcoding occurs, preserve:
  - original filename
  - original MIME type
  - original hash
  - derived/transcoded MIME separately

Kernel validation path:
- `POST /v0.1/wand/damage/validate`

Atelier API validation path:
- `POST /v1/security/wand-damage/validate`

Current implementation scope:
- validates media allowlist
- normalizes accepted evidence metadata
- returns HEIC/HEIF-aware normalized media payloads

Not implemented yet:
- media upload persistence
- preview pipeline
- automated damage classifier
- key-epoch scrambling
- guild message envelope binding
