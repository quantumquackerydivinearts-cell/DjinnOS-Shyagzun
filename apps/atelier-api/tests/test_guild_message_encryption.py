from __future__ import annotations

import base64
import hashlib
import os
import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from atelier_api.main import (
    _atelier_service,
    _capability_context,
    _role_context,
    _workshop_context,
    app,
)
from atelier_api.services import AtelierService


def _temple_source() -> dict[str, object]:
    return {
        "schema_family": "temple_entropy_source",
        "schema_version": "v1",
        "provenance_id": "garden.north-bed.epoch3",
        "source_type": "garden_observation",
        "state_digest": "temple_state_123",
        "garden_id": "temple.main",
        "plot_id": "north-bed",
    }


def _theatre_source() -> dict[str, object]:
    return {
        "schema_family": "theatre_entropy_source",
        "schema_version": "v1",
        "provenance_id": "theatre.performance.esoteric_01",
        "source_type": "performance_upload",
        "media_digest": "theatre_media_456",
        "performance_id": "esoteric_01",
        "upload_id": "upload_01",
    }


def test_encrypt_guild_message_runtime_emits_envelope() -> None:
    payload = AtelierService._encrypt_guild_message_runtime(
        guild_id="guild.alchemy",
        channel_id="hall.notice",
        sender_id="player",
        wand_id="wand_001",
        message_text="Meet in the hall at dusk.",
        thread_id="thread_001",
        recipient_distribution_id="distribution.remote.one",
        recipient_guild_id="guild.remote",
        recipient_channel_id="channel.remote",
        recipient_actor_id="remote-player",
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
    assert payload["recipient_distribution_id"] == "distribution.remote.one"
    assert payload["recipient_guild_id"] == "guild.remote"
    assert payload["recipient_channel_id"] == "channel.remote"
    assert payload["recipient_actor_id"] == "remote-player"
    assert base64.b64decode(payload["ciphertext_b64"])
    assert base64.b64decode(payload["nonce_b64"])
    assert len(payload["mac_hex"]) == 64
    assert len(str(payload["plaintext_digest"])) == 64
    derivation = payload["derivation"]
    assert derivation["temple_entropy_digest"] == hashlib.sha256(b"temple_digest_123").hexdigest()
    assert derivation["theatre_entropy_digest"] == hashlib.sha256(b"theatre_digest_456").hexdigest()


def test_encrypt_guild_message_derives_semantic_dispatch_metadata() -> None:
    svc = AtelierService(repo=None, kernel=None)  # type: ignore[arg-type]
    envelope = svc.encrypt_guild_message(
        guild_id="guild.alchemy",
        channel_id="hall.notice",
        sender_id="player",
        wand_id="wand_001",
        message_text="Soa Myk Kysael",
        metadata={"purpose": "semantic_dispatch"},
    )
    semantic_dispatch = envelope["metadata"]["semantic_runtime_dispatch"]
    assert semantic_dispatch["dispatch_channel"] == "packet"
    assert semantic_dispatch["persistence_mode"] == "persistent"
    assert semantic_dispatch["consensus_mode"] == "authoritative_commit"


def test_encrypt_and_decrypt_guild_message_roundtrip() -> None:
    envelope = AtelierService._encrypt_guild_message_runtime(
        guild_id="guild.alchemy",
        channel_id="hall.notice",
        sender_id="player",
        wand_id="wand_001",
        wand_passkey_ward="north-ash-ward",
        message_text="Meet in the hall at dusk.",
        thread_id="thread_001",
        recipient_distribution_id="distribution.remote.one",
        recipient_guild_id="guild.remote",
        recipient_channel_id="channel.remote",
        recipient_actor_id="remote-player",
        temple_entropy_digest="temple_digest_123",
        theatre_entropy_digest="theatre_digest_456",
        attestation_media_digests=["abc", "def"],
        metadata={"purpose": "guild_notice"},
    )
    svc = AtelierService(repo=None, kernel=None)  # type: ignore[arg-type]
    result = svc.decrypt_guild_message(
        envelope=envelope,
        wand_id="wand_001",
        wand_passkey_ward="north-ash-ward",
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


def test_decrypt_guild_message_fails_with_wrong_passkey_ward() -> None:
    envelope = AtelierService._encrypt_guild_message_runtime(
        guild_id="guild.alchemy",
        channel_id="hall.notice",
        sender_id="player",
        wand_id="wand_001",
        wand_passkey_ward="correct-ward",
        message_text="Meet in the hall at dusk.",
        temple_entropy_digest="temple_digest_123",
        theatre_entropy_digest="theatre_digest_456",
        attestation_media_digests=["abc", "def"],
        metadata={"purpose": "guild_notice"},
    )
    svc = AtelierService(repo=None, kernel=None)  # type: ignore[arg-type]
    result = svc.decrypt_guild_message(
        envelope=envelope,
        wand_id="wand_001",
        wand_passkey_ward="wrong-ward",
        temple_entropy_digest="temple_digest_123",
        theatre_entropy_digest="theatre_digest_456",
        attestation_media_digests=["abc", "def"],
        temple_entropy_source={},
        theatre_entropy_source={},
        attestation_sources=[],
        metadata={"purpose": "guild_notice"},
    )
    assert result["verified"] is False


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
    svc.register_distribution(
        distribution_id="distribution.remote.one",
        display_name="Remote One",
        base_url="https://remote.one.example",
        transport_kind="https",
        public_key_ref="pk_remote_one",
        guild_ids=["guild.remote"],
        metadata={"source": "test"},
    )
    envelope = svc.encrypt_guild_message(
        guild_id="guild.atelier",
        channel_id="hall.general",
        sender_id="player",
        wand_id="wand_001",
        message_text="cipher me",
        conversation_id="conv_atelier_remote_001",
        conversation_kind="guild_federated",
        thread_id="thread_001",
        sender_member_id="player",
        recipient_member_id="remote-player",
        recipient_distribution_id="distribution.remote.one",
        recipient_guild_id="guild.remote",
        recipient_channel_id="channel.remote",
        recipient_actor_id="remote-player",
        temple_entropy_digest="temple_digest_123",
        theatre_entropy_digest="theatre_digest_456",
        attestation_media_digests=["abc"],
        temple_entropy_source=_temple_source(),
        theatre_entropy_source=_theatre_source(),
        attestation_sources=[{"filename": "wand.heic", "sha256": "abc"}],
        metadata={"purpose": "test"},
    )
    persisted = svc.persist_guild_message_envelope(envelope=envelope, metadata={"source": "test"})
    assert str(persisted["message_id"]).startswith("gmsg_")
    assert "guild_messages" in str(persisted["storage_path"])
    history = svc.list_guild_message_history(guild_id="guild.atelier", channel_id="hall.general", thread_id="thread_001")
    assert len(history) == 1
    assert history[0]["envelope"]["recipient_distribution_id"] == "distribution.remote.one"

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
            conversation_id="conv_atelier_local_001",
            conversation_kind="guild_channel",
            thread_id="thread_001",
            sender_member_id="player",
            recipient_member_id=None,
            recipient_distribution_id=None,
            recipient_guild_id=None,
            recipient_channel_id=None,
            recipient_actor_id=None,
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


def test_persist_guild_message_envelope_uses_semantic_storage_bucket() -> None:
    tmp_path = Path("c:/DjinnOS/.tmp-test-semantic-storage")
    if tmp_path.exists():
        shutil.rmtree(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    os.environ["ATELIER_SECURITY_STATE_DIR"] = str(tmp_path)
    svc = AtelierService(repo=None, kernel=None)  # type: ignore[arg-type]
    envelope = svc.encrypt_guild_message(
        guild_id="guild.alchemy",
        channel_id="hall.notice",
        sender_id="player",
        wand_id="wand_001",
        message_text="Soa Myk Kysael",
        metadata={"purpose": "semantic_storage"},
    )
    persisted = svc.persist_guild_message_envelope(envelope=envelope, metadata={"purpose": "semantic_storage"})
    assert persisted["semantic_storage_bucket"] == "persistent"
    assert "guild_messages\\persistent\\" in str(persisted["storage_path"]) or "guild_messages/persistent/" in str(persisted["storage_path"])
    os.environ.pop("ATELIER_SECURITY_STATE_DIR", None)
    shutil.rmtree(tmp_path)


def test_get_wand_status_reports_latest_epoch() -> None:
    tmp_path = Path("c:/DjinnOS/.tmp-test-security-status")
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
    record = svc.persist_wand_damage_attestation(
        wand_id="wand_002",
        notifier_id="Zo@user",
        damage_state="cracked",
        event_tag="lineage_shift",
        media=[{"filename": "wand.heic", "mime_type": "image/heic", "sha256": "def"}],
        payload={"source": "test"},
        actor_id="player",
        workshop_id="main",
    )
    svc.transition_wand_key_epoch(
        wand_id="wand_002",
        attestation_record_id=str(record["record_id"]),
        notifier_id="Zo@user",
        previous_epoch_id=None,
        damage_state="cracked",
        temple_entropy_digest="temple_digest_123",
        theatre_entropy_digest="theatre_digest_456",
        attestation_media_digests=["def"],
        revoked=False,
        metadata={"reason": "test"},
    )
    status = svc.get_wand_status(wand_id="wand_002")
    assert status["wand_id"] == "wand_002"
    assert status["revoked"] is False
    assert status["status"] == "active"
    assert status["attestation_count"] == 1
    assert status["epoch_count"] == 1
    assert status["latest_epoch"]["damage_state"] == "cracked"
    os.environ.pop("ATELIER_SECURITY_STATE_DIR", None)
    shutil.rmtree(tmp_path)


def test_mix_entropy_rejects_invalid_nonempty_source_contract() -> None:
    svc = AtelierService(repo=None, kernel=None)  # type: ignore[arg-type]
    try:
        svc.mix_entropy(
            wand_id="wand_001",
            temple_entropy_digest=None,
            theatre_entropy_digest=None,
            attestation_media_digests=[],
            temple_entropy_source={"plot": "north-bed"},
            theatre_entropy_source={},
            attestation_sources=[],
            context={"source": "test"},
        )
        assert False, "expected temple source contract failure"
    except ValueError as exc:
        assert str(exc) == "temple_entropy_source_schema_family_invalid"


def test_wand_epoch_transition_revocation_requires_steward() -> None:
    class _ServiceStub:
        def transition_wand_key_epoch(self, **kwargs):
            return {"epoch_id": "wep_stub", "revoked": kwargs["revoked"]}

    app.dependency_overrides[_capability_context] = lambda: type("CapCtx", (), {"actor_id": "tester", "capabilities": frozenset({"lesson.read"})})()
    app.dependency_overrides[_workshop_context] = lambda: type(
        "WsCtx",
        (),
        {"identity": type("WsIdentity", (), {"artisan_id": "artisan", "workshop_id": "main"})()},
    )()
    app.dependency_overrides[_role_context] = lambda: type("RoleCtx", (), {"role": "senior_artisan"})()
    app.dependency_overrides[_atelier_service] = lambda: _ServiceStub()
    try:
        client = TestClient(app)
        response = client.post(
            "/v1/security/wand/epoch-transition",
            json={
                "wand_id": "wand_001",
                "attestation_record_id": "watt_001",
                "notifier_id": "Zo@user",
                "damage_state": "broken",
                "revoked": True,
            },
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "steward_required_for_revocation"
    finally:
        app.dependency_overrides.clear()


def test_register_and_list_wand_registry_file_fallback() -> None:
    tmp_path = Path("c:/DjinnOS/.tmp-test-wand-registry")
    if tmp_path.exists():
        shutil.rmtree(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    os.environ["ATELIER_SECURITY_STATE_DIR"] = str(tmp_path)
    svc = AtelierService(repo=None, kernel=None)  # type: ignore[arg-type]

    record = svc.register_wand(
        wand_id="wand_registry_001",
        maker_id="maker.quant",
        maker_date="2026-03-08",
        atelier_origin="atelier.guildhall",
        material_profile={"wood": "ash", "core": "silver-thread"},
        dimensions={"length_mm": 340, "shaft_diameter_mm": 11, "mass_g": 31},
        structural_fingerprint="fp_001",
        craft_record_hash="craft_hash_001",
        ownership_chain=[{"owner_id": "player", "epoch": "creation"}],
        metadata={"display_name": "North Ash Wand"},
    )
    assert record["wand_id"] == "wand_registry_001"
    assert record["maker_id"] == "maker.quant"

    stored = tmp_path / "wand_registry" / "wand_registry_001.json"
    assert stored.exists()

    loaded = svc.get_wand_registry_entry(wand_id="wand_registry_001")
    assert loaded["craft_record_hash"] == "craft_hash_001"
    assert loaded["material_profile"]["wood"] == "ash"
    assert loaded["dimensions"]["length_mm"] == 340
    assert loaded["maker_date"] == "2026-03-08"
    assert loaded["wand_spec"]["dimensions"]["mass_g"] == 31

    records = svc.list_wand_registry(limit=10)
    assert any(item["wand_id"] == "wand_registry_001" for item in records)

    os.environ.pop("ATELIER_SECURITY_STATE_DIR", None)
    shutil.rmtree(tmp_path)


def test_register_wand_endpoint_allows_standard_registry_access() -> None:
    class _ServiceStub:
        def register_wand(self, **kwargs):
            return {
                "wand_id": kwargs["wand_id"],
                "maker_id": kwargs["maker_id"],
                "maker_date": kwargs["maker_date"],
                "atelier_origin": kwargs["atelier_origin"],
                "status": "active",
            }

    app.dependency_overrides[_capability_context] = lambda: type("CapCtx", (), {"actor_id": "tester", "capabilities": frozenset({"lesson.read"})})()
    app.dependency_overrides[_workshop_context] = lambda: type(
        "WsCtx",
        (),
        {"identity": type("WsIdentity", (), {"artisan_id": "artisan", "workshop_id": "main"})()},
    )()
    app.dependency_overrides[_role_context] = lambda: type("RoleCtx", (), {"role": "senior_artisan"})()
    app.dependency_overrides[_atelier_service] = lambda: _ServiceStub()
    try:
        client = TestClient(app)
        response = client.post(
            "/v1/security/wands/register",
            json={
                "wand_id": "wand_001",
                "maker_id": "maker.quant",
                "maker_date": "2026-03-08",
                "atelier_origin": "atelier.guildhall",
            },
        )
        assert response.status_code == 200
        assert response.json()["wand_id"] == "wand_001"
    finally:
        app.dependency_overrides.clear()


def test_register_and_list_guild_registry_file_fallback() -> None:
    tmp_path = Path("c:/DjinnOS/.tmp-test-guild-registry")
    if tmp_path.exists():
        shutil.rmtree(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    os.environ["ATELIER_SECURITY_STATE_DIR"] = str(tmp_path)
    svc = AtelierService(repo=None, kernel=None)  # type: ignore[arg-type]

    record = svc.register_guild(
        guild_id="guild.atelier",
        display_name="Atelier Guild",
        distribution_id="distribution.quantumquackery.main",
        owner_artisan_id="artisan-desktop",
        owner_profile_name="Artisan",
        owner_profile_email="artisan@example.com",
        member_profiles=[{"actor_id": "player", "display_name": "Artisan"}],
        charter={"trust_model": "wand_registry"},
        metadata={"source": "test"},
    )
    assert record["guild_id"] == "guild.atelier"
    assert record["owner_artisan_id"] == "artisan-desktop"

    stored = tmp_path / "guild_registry" / "guild.atelier.json"
    assert stored.exists()

    loaded = svc.get_guild_registry_entry(guild_id="guild.atelier")
    assert loaded["distribution_id"] == "distribution.quantumquackery.main"
    assert loaded["member_profiles"][0]["actor_id"] == "player"

    records = svc.list_guild_registry(limit=10)
    assert any(item["guild_id"] == "guild.atelier" for item in records)

    os.environ.pop("ATELIER_SECURITY_STATE_DIR", None)
    shutil.rmtree(tmp_path)


def test_register_and_list_distribution_registry_file_fallback() -> None:
    tmp_path = Path("c:/DjinnOS/.tmp-test-distribution-registry")
    if tmp_path.exists():
        shutil.rmtree(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    os.environ["ATELIER_SECURITY_STATE_DIR"] = str(tmp_path)
    svc = AtelierService(repo=None, kernel=None)  # type: ignore[arg-type]

    record = svc.register_distribution(
        distribution_id="distribution.quantumquackery.remote",
        display_name="Quantum Quackery Remote",
        base_url="https://remote.quantumquackery.org",
        transport_kind="https",
        public_key_ref="pk_remote_001",
        guild_ids=["guild.atelier", "guild.remote"],
        metadata={"source": "test"},
    )
    assert record["distribution_id"] == "distribution.quantumquackery.remote"
    listed = svc.list_distribution_registry(limit=10)
    assert len(listed) == 1
    loaded = svc.get_distribution_registry_entry(distribution_id="distribution.quantumquackery.remote")
    assert loaded["base_url"] == "https://remote.quantumquackery.org"
    assert loaded["guild_ids"] == ["guild.atelier", "guild.remote"]
    os.environ.pop("ATELIER_SECURITY_STATE_DIR", None)
    shutil.rmtree(tmp_path)


def test_distribution_key_discovery_and_relay_status_update() -> None:
    tmp_path = Path("c:/DjinnOS/.tmp-test-distribution-relay")
    if tmp_path.exists():
        shutil.rmtree(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    os.environ["ATELIER_SECURITY_STATE_DIR"] = str(tmp_path)
    svc = AtelierService(repo=None, kernel=None)  # type: ignore[arg-type]

    svc.register_distribution(
        distribution_id="distribution.quantumquackery.remote",
        display_name="Quantum Quackery Remote",
        base_url="https://remote.quantumquackery.org",
        transport_kind="https",
        public_key_ref="pk_remote_001",
        protocol_family="guild_message_signal_artifice",
        protocol_version="v1",
        supported_protocol_versions=["v1"],
        guild_ids=["guild.remote"],
        metadata={"source": "test"},
    )
    svc.register_guild(
        guild_id="guild.remote",
        display_name="Remote Guild",
        distribution_id="distribution.quantumquackery.remote",
        owner_artisan_id="artisan.remote",
        owner_profile_name="Remote Artisan",
        owner_profile_email="remote@example.com",
        member_profiles=[],
        charter={"channels": ["hall.remote", "hall.notice"]},
        metadata={"source": "test"},
    )
    handshake = svc.register_distribution_handshake(
        distribution_id="distribution.quantumquackery.remote",
        local_distribution_id="distribution.quantumquackery.main",
        remote_public_key_ref="pk_remote_001",
        handshake_mode="mutual_hmac",
        protocol_family="guild_message_signal_artifice",
        local_protocol_version="v1",
        remote_protocol_version="v1",
        negotiated_protocol_version="v1",
        metadata={"source": "test"},
    )
    assert handshake["distribution_id"] == "distribution.quantumquackery.remote"
    descriptor = svc.get_distribution_key_descriptor(distribution_id="distribution.quantumquackery.remote")
    assert descriptor["public_key_ref"] == "pk_remote_001"
    capabilities = svc.discover_distribution_capabilities(distribution_id="distribution.quantumquackery.remote")
    assert capabilities["guilds"][0]["channels"] == ["hall.remote", "hall.notice"]
    assert capabilities["messaging_protocol"]["distribution"]["version"] == "v1"
    assert capabilities["messaging_protocol"]["handshake"]["negotiated_version"] == "v1"

    envelope = svc.encrypt_guild_message(
        guild_id="guild.atelier",
        channel_id="hall.general",
        sender_id="player",
        wand_id="wand_001",
        message_text="remote hello",
        conversation_id="conv_remote_hello",
        conversation_kind="guild_federated",
        thread_id="thread_001",
        sender_member_id="player",
        recipient_member_id="remote-player",
        recipient_distribution_id="distribution.quantumquackery.remote",
        recipient_guild_id="guild.remote",
        recipient_channel_id="hall.remote",
        recipient_actor_id="remote-player",
        temple_entropy_digest="temple_digest_123",
        theatre_entropy_digest="theatre_digest_456",
        attestation_media_digests=["abc"],
        temple_entropy_source=_temple_source(),
        theatre_entropy_source=_theatre_source(),
        attestation_sources=[],
        metadata={"purpose": "relay_test"},
    )
    assert envelope["metadata"]["recipient_distribution_key"]["public_key_ref"] == "pk_remote_001"
    assert envelope["metadata"]["recipient_distribution_protocol"]["version"] == "v1"
    assert envelope["metadata"]["recipient_distribution_handshake_protocol"]["negotiated_version"] == "v1"
    persisted = svc.persist_guild_message_envelope(envelope=envelope, metadata={"source": "test"})
    assert persisted["relay_status"] == "remote_pending"
    updated = svc.update_guild_message_relay_status(
        message_id=str(persisted["message_id"]),
        relay_status="delivered_remote",
        receipt={"distribution_id": "distribution.quantumquackery.remote", "relay_id": "relay_001"},
    )
    assert updated["relay_status"] == "delivered_remote"
    assert len(updated["delivery_receipts"]) == 1
    assert updated["delivery_receipts"][0]["signature_family"] == "distribution_receipt_hmac_v1"
    history = svc.list_guild_message_history(guild_id="guild.atelier", channel_id="hall.general", thread_id="thread_001")
    assert history[0]["metadata"]["relay_status"] == "delivered_remote"
    os.environ.pop("ATELIER_SECURITY_STATE_DIR", None)
    shutil.rmtree(tmp_path)


def test_encrypt_rejects_incompatible_distribution_protocol() -> None:
    tmp_path = Path("c:/DjinnOS/.tmp-test-distribution-protocol")
    if tmp_path.exists():
        shutil.rmtree(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    os.environ["ATELIER_SECURITY_STATE_DIR"] = str(tmp_path)
    svc = AtelierService(repo=None, kernel=None)  # type: ignore[arg-type]

    svc.register_distribution(
        distribution_id="distribution.quantumquackery.remote",
        display_name="Quantum Quackery Remote",
        base_url="https://remote.quantumquackery.org",
        transport_kind="https",
        public_key_ref="pk_remote_001",
        protocol_family="guild_message_signal_artifice",
        protocol_version="v0",
        supported_protocol_versions=["v0"],
        guild_ids=["guild.remote"],
        metadata={"source": "test"},
    )

    try:
        svc.encrypt_guild_message(
            guild_id="guild.atelier",
            channel_id="hall.general",
            sender_id="player",
            wand_id="wand_001",
            message_text="remote hello",
            recipient_distribution_id="distribution.quantumquackery.remote",
            temple_entropy_digest="temple_digest_123",
            theatre_entropy_digest="theatre_digest_456",
            attestation_media_digests=["abc"],
            temple_entropy_source=_temple_source(),
            theatre_entropy_source=_theatre_source(),
            attestation_sources=[],
            metadata={"purpose": "relay_test"},
        )
    except ValueError as exc:
        assert str(exc) == "recipient_distribution_protocol_version_unsupported"
    else:
        raise AssertionError("expected protocol compatibility failure")

    os.environ.pop("ATELIER_SECURITY_STATE_DIR", None)
    shutil.rmtree(tmp_path)


def test_upsert_and_list_guild_conversations_file_fallback() -> None:
    tmp_path = Path("c:/DjinnOS/.tmp-test-guild-conversations")
    if tmp_path.exists():
        shutil.rmtree(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    os.environ["ATELIER_SECURITY_STATE_DIR"] = str(tmp_path)
    svc = AtelierService(repo=None, kernel=None)  # type: ignore[arg-type]

    conversation = svc.upsert_guild_conversation(
        conversation_id="conv_dm_quant_player",
        conversation_kind="member_dm",
        guild_id="guild.atelier",
        channel_id="hall.direct",
        thread_id=None,
        title="Quant <> Player",
        participant_member_ids=["quant", "player"],
        participant_guild_ids=["guild.atelier"],
        distribution_id=None,
        security_session={"sender_identity_key_ref": "quant.identity", "recipient_identity_key_ref": "player.identity"},
        metadata={"source": "test"},
    )
    assert conversation["conversation_kind"] == "member_dm"
    assert conversation["security_session"]["schema_family"] == "signal_artifice_session"

    loaded = svc.get_guild_conversation(conversation_id="conv_dm_quant_player")
    assert loaded["title"] == "Quant <> Player"
    records = svc.list_guild_conversations(guild_id="guild.atelier", participant_member_id="player")
    assert any(item["conversation_id"] == "conv_dm_quant_player" for item in records)

    os.environ.pop("ATELIER_SECURITY_STATE_DIR", None)
    shutil.rmtree(tmp_path)
