from __future__ import annotations

from fastapi.testclient import TestClient

from shygazun.kernel_service import app


def test_akinenwun_lookup_ingests_dictionary() -> None:
    client = TestClient(app)
    response = client.post(
        "/v0.1/akinenwun/lookup",
        json={"akinenwun": "TyKoWuVu", "mode": "prose", "ingest": True},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["akinenwun"] == "TyKoWuVu"
    assert payload["mode"] == "prose"
    assert str(payload["frontier_hash"]).startswith("h_")
    assert payload["stored"] is True
    assert isinstance(payload["frontier"]["paths"], list)
    assert payload["dictionary_size"] >= 1


def test_akinenwun_lookup_rejects_space_separated_word() -> None:
    client = TestClient(app)
    response = client.post(
        "/v0.1/akinenwun/lookup",
        json={"akinenwun": "Ty Ko", "mode": "prose", "ingest": False},
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload["detail"] == "akinenwun must not contain spaces"
