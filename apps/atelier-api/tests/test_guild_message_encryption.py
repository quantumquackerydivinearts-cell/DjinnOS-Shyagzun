from __future__ import annotations

import base64
import hashlib
import os
import shutil
from pathlib import Path

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
    assert len(str(payload["plaintext_digest"])) == 64
    derivation = payload["derivation"]
    assert derivation["temple_entropy_digest"] == hashlib.sha256(b"temple_digest_123").hexdigest()
    assert derivation["theatre_entropy_digest"] == hashlib.sha256(b"theatre_digest_456").hexdigest()


def test_encrypt_and_decrypt_guild_message_roundtrip() -> None:
    envelope = AtelierService._encrypt_guild_message_runtime(
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
    svc = AtelierService(repo=None, kernel=None)  # type: ignore[arg-type]
    result = svc.decrypt_guild_message(
        envelope=envelope,
        wand_id="wand_001",
        temple_entropy_digest="temple_digest_123",
        theatre_entropy_digest="theatre_digest_456",
        attestation_media_digests=["abc", "def"],
        temple_entropy_source={},
        theatre_entropy_source={},
        attestation_sources=[],
        metadata={"purpose": "guild_notice"},
    )
    assert result["verified"] is True
    assert result["plaintext"] == "Meet in the hall at dusk."


def test_persist_wand_damage_attestation_writes_record() -> None:
    tmp_path = Path("c:/DjinnOS/.tmp-test-security")
    if tmp_path.exists():
        shutil.rmtree(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    os.environ["ATELIER_SECURITY_STATE_DIR"] = str(tmp_path)
    svc = AtelierService(repo=None, kernel=None)  # type: ignore[arg-type]

    class _KernelStub:
        def validate_wand_damage_attestation(self, **kwargs):
            media = kwargs["media"]
            return {
                "ok": True,
                "normalized_media": media,
                "damage_state": kwargs["damage_state"],
            }

    svc._kernel = _KernelStub()
    record = svc.persist_wand_damage_attestation(
        wand_id="wand_001",
        notifier_id="Zo@user",
        damage_state="broken",
        event_tag="breakproof_01",
        media=[{"filename": "wand.heic", "mime_type": "image/heic", "sha256": "abc"}],
        payload={"source": "test"},
        actor_id="player",
        workshop_id="main",
    )
    assert str(record["record_id"]).startswith("watt_")
    stored = tmp_path / "wand_attestations" / f"{record['record_id']}.json"
    assert stored.exists()
    os.environ.pop("ATELIER_SECURITY_STATE_DIR", None)
    shutil.rmtree(tmp_path)


def test_list_and_transition_wand_epochs() -> None:
    tmp_path = Path("c:/DjinnOS/.tmp-test-security-epochs")
    if tmp_path.exists():
        shutil.rmtree(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    os.environ["ATELIER_SECURITY_STATE_DIR"] = str(tmp_path)
    svc = AtelierService(repo=None, kernel=None)  # type: ignore[arg-type]

    class _KernelStub:
        def validate_wand_damage_attestation(self, **kwargs):
            media = kwargs["media"]
            return {
                "ok": True,
                "normalized_media": media,
                "damage_state": kwargs["damage_state"],
            }

    svc._kernel = _KernelStub()
    record = svc.persist_wand_damage_attestation(
        wand_id="wand_001",
        notifier_id="Zo@user",
        damage_state="broken",
        event_tag="breakproof_01",
        media=[{"filename": "wand.heic", "mime_type": "image/heic", "sha256": "abc"}],
        payload={"source": "test"},
        actor_id="player",
        workshop_id="main",
    )
    history = svc.list_wand_damage_attestations(wand_id="wand_001", limit=10)
    assert len(history) == 1
    epoch = svc.transition_wand_key_epoch(
        wand_id="wand_001",
        attestation_record_id=str(record["record_id"]),
        notifier_id="Zo@user",
        previous_epoch_id=None,
        damage_state="broken",
        temple_entropy_digest="temple_digest_123",
        theatre_entropy_digest="theatre_digest_456",
        attestation_media_digests=["abc"],
        revoked=True,
        metadata={"reason": "fracture"},
    )
    assert str(epoch["epoch_id"]).startswith("wep_")
    epochs = svc.list_wand_key_epochs(wand_id="wand_001", limit=10)
    assert len(epochs) == 1
    assert epochs[0]["revoked"] is True
    os.environ.pop("ATELIER_SECURITY_STATE_DIR", None)
    shutil.rmtree(tmp_path)


def test_guild_message_history_and_revocation_gate() -> None:
    tmp_path = Path("c:/DjinnOS/.tmp-test-security-history")
    if tmp_path.exists():
        shutil.rmtree(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    os.environ["ATELIER_SECURITY_STATE_DIR"] = str(tmp_path)
    svc = AtelierService(repo=None, kernel=None)  # type: ignore[arg-type]

    class _KernelStub:
        def validate_wand_damage_attestation(self, **kwargs):
            return {
                "ok": True,
                "normalized_media": kwargs["media"],
                "damage_state": kwargs["damage_state"],
            }

    svc._kernel = _KernelStub()
    envelope = svc.encrypt_guild_message(
        guild_id="guild.atelier",
        channel_id="hall.general",
        sender_id="player",
        wand_id="wand_001",
        message_text="cipher me",
        thread_id="thread_001",
        temple_entropy_digest="temple_digest_123",
        theatre_entropy_digest="theatre_digest_456",
        attestation_media_digests=["abc"],
        temple_entropy_source={"plot": "north-bed", "epoch": 3},
        theatre_entropy_source={"performance": "esoteric_01"},
        attestation_sources=[{"filename": "wand.heic", "sha256": "abc"}],
        metadata={"purpose": "test"},
    )
    persisted = svc.persist_guild_message_envelope(envelope=envelope, metadata={"source": "test"})
    assert str(persisted["message_id"]).startswith("gmsg_")
    history = svc.list_guild_message_history(guild_id="guild.atelier", channel_id="hall.general", thread_id="thread_001")
    assert len(history) == 1

    record = svc.persist_wand_damage_attestation(
        wand_id="wand_001",
        notifier_id="Zo@user",
        damage_state="broken",
        event_tag="fracture",
        media=[{"filename": "wand.heic", "mime_type": "image/heic", "sha256": "abc"}],
        payload={"source": "test"},
        actor_id="player",
        workshop_id="main",
    )
    svc.transition_wand_key_epoch(
        wand_id="wand_001",
        attestation_record_id=str(record["record_id"]),
        notifier_id="Zo@user",
        previous_epoch_id=None,
        damage_state="broken",
        temple_entropy_digest="temple_digest_123",
        theatre_entropy_digest="theatre_digest_456",
        attestation_media_digests=["abc"],
        revoked=True,
        metadata={"reason": "fracture"},
    )
    try:
        svc.encrypt_guild_message(
            guild_id="guild.atelier",
            channel_id="hall.general",
            sender_id="player",
            wand_id="wand_001",
            message_text="blocked",
            thread_id="thread_001",
            temple_entropy_digest="temple_digest_123",
            theatre_entropy_digest="theatre_digest_456",
            attestation_media_digests=["abc"],
            temple_entropy_source={},
            theatre_entropy_source={},
            attestation_sources=[],
            metadata={"purpose": "test"},
        )
        assert False, "expected wand_revoked"
    except ValueError as exc:
        assert str(exc) == "wand_revoked"
    os.environ.pop("ATELIER_SECURITY_STATE_DIR", None)
    shutil.rmtree(tmp_path)
