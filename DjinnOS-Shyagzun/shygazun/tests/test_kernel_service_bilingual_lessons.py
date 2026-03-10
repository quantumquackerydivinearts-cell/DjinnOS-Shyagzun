from __future__ import annotations

from fastapi.testclient import TestClient

from shygazun.kernel_service import app


def test_lessons_endpoint_returns_canonical_lessons() -> None:
    client = TestClient(app)
    response = client.get("/v0.1/shygazun/lessons")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] >= 11
    lesson_ids = {lesson["lesson_id"] for lesson in payload["lessons"]}
    assert "pronoun_aliases_sextal_wu_v1" in lesson_ids
    assert "directional_projection_over_surface_order_v1" in lesson_ids
    assert "animal_aliases_whale_affection_v2" in lesson_ids
    assert "feature_aliases_animacy_embodiment_number_v1" in lesson_ids
    assert "anatomy_structural_metaphor_v1" in lesson_ids
    assert "anatomy_body_spirit_axes_v1" in lesson_ids
    assert "creature_form_regimes_v1" in lesson_ids
    assert "time_word_process_bias_v1" in lesson_ids
    assert "aster_chirality_topology_v1" in lesson_ids
    assert "grapevine_systems_semantics_v1" in lesson_ids
    assert "cannabis_axis_semantics_v1" in lesson_ids


def test_bilingual_project_resolves_pronoun_alias_from_lesson_registry() -> None:
    client = TestClient(app)
    response = client.post("/v0.1/shygazun/project", json={"source_text": "Awu"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["source_text"] == "Awu"
    assert payload["tokens"][0]["kind"] == "pronoun_alias"
    assert payload["tokens"][0]["english_alias"] == "I"
    assert payload["tokens"][0]["bytes"] == [98, 45]
    assert payload["tokens"][0]["symbols"] == ["A", "Wu"]


def test_bilingual_project_honors_exact_projection_example() -> None:
    client = TestClient(app)
    response = client.post("/v0.1/shygazun/project", json={"source_text": "Aely Melkowuvune Awu"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["authoritative_projection"]["english"] == "I love whales"
    assert payload["authoritative_projection"]["literal_gloss"] == "Love whales I"
    assert payload["authoritative_projection"]["lesson_id"] == "directional_projection_over_surface_order_v1"
    assert payload["composed_features"]["person"] == 1


def test_bilingual_project_can_derive_projection_from_lesson_pattern() -> None:
    client = TestClient(app)
    response = client.post("/v0.1/shygazun/project", json={"source_text": "Aely Melkowuvune Owu"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["authoritative_projection"]["english"] == "We love whales"
    assert payload["authoritative_projection"]["literal_gloss"] == "Love whales We"
    assert payload["authoritative_projection"]["authority_level"] == "lesson_regime_match"
    assert payload["authoritative_projection"]["regime_id"] == "predicate_patient_pronoun_reordering"
    assert payload["composed_features"]["animacy"] == "animate"
    assert "animacy:animate" in payload["surface_lowerings"]["code_surface"]["feature_tags"]
    assert payload["surface_lowerings"]["placement_graph"]["projection_hints"]["animate"] is True


def test_bilingual_project_regime_extends_across_pronoun_lattice() -> None:
    client = TestClient(app)
    response = client.post("/v0.1/shygazun/project", json={"source_text": "Aely Melkowuvune Iwu"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["authoritative_projection"]["english"] == "You love whales"
    assert payload["authoritative_projection"]["literal_gloss"] == "Love whales You"
    assert payload["authoritative_projection"]["authority_level"] == "lesson_regime_match"


def test_bilingual_project_composes_feature_alias_state() -> None:
    client = TestClient(app)
    response = client.post("/v0.1/shygazun/project", json={"source_text": "Va Vi Vy"})
    assert response.status_code == 200
    payload = response.json()
    features = payload["composed_features"]
    assert features["animacy"] == "animate"
    assert features["number"] == "singular"
    assert features["embodiment"] == ["body", "spirit"] or features["embodiment"] == ["spirit", "body"]
    assert isinstance(features["_sources"], list)


def test_bilingual_project_feature_bundle_survives_on_lexeme_aliases() -> None:
    client = TestClient(app)
    response = client.post("/v0.1/shygazun/project", json={"source_text": "Melkowuvune"})
    assert response.status_code == 200
    payload = response.json()
    token = payload["tokens"][0]
    assert token["kind"] == "lexeme_alias"
    assert token["feature_bundle"]["animacy"] == "animate"
    assert token["feature_bundle"]["number"] == "plural"


def test_bilingual_project_verifies_structural_metaphor_regime_on_whale_alias() -> None:
    client = TestClient(app)
    response = client.post("/v0.1/shygazun/project", json={"source_text": "Melkowuvune"})
    assert response.status_code == 200
    payload = response.json()
    verification = next(
        item for item in payload["structural_verifications"]
        if item["regime_id"] == "rose_daisy_mediated_by_sakura_validated_by_lotus"
    )
    assert verification["verified"] is True
    assert "Rose" in verification["tongues_seen"]
    assert "Daisy" in verification["tongues_seen"]
    assert "Sakura" in verification["tongues_seen"]
    assert "Lotus" in verification["tongues_seen"]
    assert verification["derived_features"]["anatomy_derivation"] == "rose_daisy_structural_metaphor"
    assert payload["composed_features"]["anatomy_derivation"] == "rose_daisy_structural_metaphor"
    assert payload["composed_features"]["validation_mode"] == "lotus"
    creature_regime = next(
        item for item in payload["structural_verifications"]
        if item["regime_id"] == "animate_processual_creature_alias"
    )
    assert creature_regime["verified"] is True
    assert payload["composed_features"]["ontic_domain"] == "creature"
    assert payload["composed_features"]["cluster_logic"] == "kael_implicit"


def test_bilingual_project_verifies_body_spirit_axes_and_emits_trust_contract() -> None:
    client = TestClient(app)
    response = client.post("/v0.1/shygazun/project", json={"source_text": "Vi Vy"})
    assert response.status_code == 200
    payload = response.json()
    verification = next(
        item for item in payload["structural_verifications"]
        if item["regime_id"] == "sakura_embodiment_axes_present"
    )
    assert verification["verified"] is True
    assert "Sakura" in verification["tongues_seen"]
    assert "body" in verification["derived_features"]["anatomy_axes"]
    assert "spirit" in verification["derived_features"]["anatomy_axes"]
    trust = payload["trust_contract"]
    assert trust["coverage"]["total_tokens"] == 2
    assert trust["coverage"]["unresolved_tokens"] == 0
    assert trust["score"] > 0
    assert trust["downstream_readiness"]["code_surface_safe"] is True
    assert trust["downstream_readiness"]["anatomy_surface_safe"] is True
    assert "body" in payload["composed_features"]["anatomy_axes"]
    assert "spirit" in payload["composed_features"]["anatomy_axes"]


def test_bilingual_project_derives_code_and_graph_lowerings_from_features() -> None:
    client = TestClient(app)
    response = client.post("/v0.1/shygazun/project", json={"source_text": "Va Vi Vy"})
    assert response.status_code == 200
    payload = response.json()
    code_surface = payload["surface_lowerings"]["code_surface"]
    placement_graph = payload["surface_lowerings"]["placement_graph"]
    assert "animacy:animate" in code_surface["feature_tags"]
    assert "embodiment:body" in code_surface["feature_tags"]
    assert "embodiment:spirit" in code_surface["feature_tags"]
    assert placement_graph["projection_hints"]["animate"] is True
    assert "body" in placement_graph["projection_hints"]["embodiment_axes"]
    assert "spirit" in placement_graph["projection_hints"]["embodiment_axes"]


def test_bilingual_project_derives_time_word_process_bias() -> None:
    client = TestClient(app)
    response = client.post("/v0.1/shygazun/project", json={"source_text": "YWu"})
    assert response.status_code == 200
    payload = response.json()
    token = payload["tokens"][0]
    assert token["kind"] == "akinenwun_surface"
    assert token["feature_bundle"]["time_bearing"] is True
    assert token["feature_bundle"]["probable_verb_stem"] is True
    verification = next(
        item for item in payload["structural_verifications"]
        if item["regime_id"] == "time_bearing_probable_verb_stem"
    )
    assert verification["verified"] is True
    assert payload["composed_features"]["stem_likelihood"] == "verbal"
    assert payload["composed_features"]["process_bias"] == "high"


def test_bilingual_project_derives_aster_chirality_topology_and_space_ops() -> None:
    client = TestClient(app)
    response = client.post("/v0.1/shygazun/project", json={"source_text": "Ry Si Ep"})
    assert response.status_code == 200
    payload = response.json()
    features = payload["composed_features"]
    assert features["chirality"] == "right"
    assert features["chiral_color_vector"] == "red"
    assert features["time_topology"] == "linear"
    assert features["space_operator"] == "assign"
    code_surface = payload["surface_lowerings"]["code_surface"]
    placement_graph = payload["surface_lowerings"]["placement_graph"]
    assert code_surface["entity_traits"]["chirality"] == "right"
    assert placement_graph["projection_hints"]["time_topology"] == "linear"
    assert placement_graph["projection_hints"]["space_operator"] == "assign"


def test_bilingual_project_derives_grapevine_systems_features() -> None:
    client = TestClient(app)
    response = client.post("/v0.1/shygazun/project", json={"source_text": "Myk Myrun Kysha Kysael"})
    assert response.status_code == 200
    payload = response.json()
    features = payload["composed_features"]
    network_role = features["network_role"]
    cluster_role = features["cluster_role"]
    if isinstance(network_role, list):
        assert "packet" in network_role
        assert "stream" in network_role
    else:
        assert network_role in {"packet", "stream"}
    if isinstance(cluster_role, list):
        assert "consensus" in cluster_role
        assert "authoritative_commit" in cluster_role
    else:
        assert cluster_role in {"consensus", "authoritative_commit"}
    assert features["commit_authority"] is True
    assert payload["surface_lowerings"]["code_surface"]["entity_traits"]["commit_authority"] is True


def test_bilingual_project_derives_cannabis_axis_projection_modes() -> None:
    client = TestClient(app)
    response = client.post("/v0.1/shygazun/project", json={"source_text": "At It Yt"})
    assert response.status_code == 200
    payload = response.json()
    features = payload["composed_features"]
    axis = features["axis"]
    assert isinstance(axis, list)
    assert "mind" in axis
    assert "space" in axis
    assert "time" in axis
    assert features["tongue_projection"] == "lotus"
    assert features["cannabis_mode"] == "nounal"
    placement_graph = payload["surface_lowerings"]["placement_graph"]
    assert "lotus" in placement_graph["projection_hints"]["tongue_projection"]


def test_bilingual_project_emits_byte_table_trace_and_semantic_trace() -> None:
    client = TestClient(app)
    response = client.post("/v0.1/shygazun/project", json={"source_text": "Melkowuvune Awu"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["byte_table_trace"]["tongue_counts"]["AppleBlossom"] >= 1
    assert payload["byte_table_trace"]["tongue_counts"]["Lotus"] >= 1
    whale = payload["tokens"][0]
    assert whale["semantic_trace"][0]["symbol"] == "Mel"
    assert any(item["tongue"] == "Daisy" and item["symbol"] == "Ne" for item in whale["semantic_trace"])


def test_bilingual_cobra_surface_emits_machine_ready_payload() -> None:
    client = TestClient(app)
    response = client.post("/v0.1/shygazun/cobra_surface", json={"source_text": "Aely Melkowuvune Owu"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["authoritative_projection"]["english"] == "We love whales"
    assert payload["code_surface"]["entity_traits"]["animacy"] == "animate"
    assert payload["placement_graph"]["projection_hints"]["animate"] is True
    assert payload["trust_contract"]["downstream_readiness"]["code_surface_safe"] is True


def test_bilingual_teach_validate_accepts_canonical_lessons() -> None:
    client = TestClient(app)
    lesson = {
        "lesson_id": "test_validate_pronoun_lesson",
        "lesson_type": "pronoun_paradigm",
        "authority": {
            "byte_table_version": "byte_table.py",
            "citations": [
                {
                    "decimal": 98,
                    "binary": "01100010",
                    "tongue": "AppleBlossom",
                    "symbol": "A",
                    "meaning": "Mind +",
                },
                {
                    "decimal": 45,
                    "binary": "00101101",
                    "tongue": "Rose",
                    "symbol": "Wu",
                    "meaning": "Process / Way",
                },
            ],
        },
        "paradigm": [
            {
                "token": "Awu",
                "english_alias": "I",
                "person": 1,
                "number": "singular",
                "distance_from_speaker_mind": "self-center",
            }
        ],
    }
    response = client.post("/v0.1/shygazun/teach/validate", json={"lessons": [lesson]})
    assert response.status_code == 200
    payload = response.json()
    assert payload["validated"] is True
    assert payload["count"] == 1
    assert payload["lessons"][0]["lesson_id"] == "test_validate_pronoun_lesson"


def test_bilingual_teach_validate_rejects_bad_citations() -> None:
    client = TestClient(app)
    lesson = {
        "lesson_id": "test_bad_lesson",
        "lesson_type": "feature_aliases",
        "authority": {
            "byte_table_version": "byte_table.py",
            "citations": [
                {
                    "decimal": 66,
                    "binary": "01000010",
                    "tongue": "Sakura",
                    "symbol": "Va",
                    "meaning": "wrong meaning",
                }
            ],
        },
    }
    response = client.post("/v0.1/shygazun/teach/validate", json={"lessons": [lesson]})
    assert response.status_code == 400
    assert "citation mismatch" in response.json()["detail"]


def test_wand_damage_validate_accepts_heic_media() -> None:
    client = TestClient(app)
    response = client.post(
        "/v0.1/wand/damage/validate",
        json={
            "wand_id": "wand_001",
            "notifier_id": "Zo@user",
            "damage_state": "broken",
            "event_tag": "fracture_attest",
            "media": [
                {
                    "filename": "wand-break.heic",
                    "mime_type": "image/heic",
                    "sha256": "abc123",
                    "size_bytes": 2048,
                    "feature_digest": "fd01",
                }
            ],
            "payload": {"damage_summary": "tip fracture"},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["heic_accepted"] is True
    assert payload["normalized_media"][0]["mime_type"] == "image/heic"
    assert payload["normalized_media"][0]["extension"] == ".heic"
    assert payload["normalized_media"][0]["heic_family"] is True


def test_wand_damage_validate_rejects_unsupported_media() -> None:
    client = TestClient(app)
    response = client.post(
        "/v0.1/wand/damage/validate",
        json={
            "wand_id": "wand_001",
            "notifier_id": "Zo@user",
            "damage_state": "broken",
            "media": [
                {
                    "filename": "wand-break.gif",
                    "mime_type": "image/gif",
                    "size_bytes": 2048,
                }
            ],
        },
    )
    assert response.status_code == 422
    assert "wand_damage_media_mime_unsupported" in response.json()["detail"]
