from __future__ import annotations

import base64

from atelier_api.services import AtelierService


def test_encrypt_guild_message_runtime_emits_envelope() -> None:
    payload = AtelierService._encrypt_guild_message_runtime(
        guild_id="guild.alchemy",
        channel_id="hall.notice",
        sender_id="player",
        wand_id="wand_001",
        message_text="Meet in the hall at dusk.",
        thread_id="thread_001",
        temple_entropy_digest="temple_digest_123",
        theatre_entropy_digest="theatre_digest_456",
        attestation_media_digests=["abc", "def"],
        metadata={"purpose": "guild_notice"},
    )
    assert payload["schema_family"] == "guild_message_envelope"
    assert payload["schema_version"] == "v1"
    assert payload["cipher_family"] == "experimental_hash_stream_v1"
    assert payload["guild_id"] == "guild.alchemy"
    assert payload["wand_id"] == "wand_001"
    assert base64.b64decode(payload["ciphertext_b64"])
    assert base64.b64decode(payload["nonce_b64"])
    assert len(payload["mac_hex"]) == 64
    derivation = payload["derivation"]
    assert derivation["temple_entropy_digest"] == "temple_digest_123"
    assert derivation["theatre_entropy_digest"] == "theatre_digest_456"
