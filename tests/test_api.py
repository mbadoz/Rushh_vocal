from copy import deepcopy
from api.catalog import DEFAULT
from api.store import db, get
from api.main import new_run

WORKER = {"Authorization": "Bearer worker-test-only"}


def test_auth_csrf_and_worker_separation(client):
    client.cookies.clear()
    assert client.get("/api/compositions").status_code == 401
    assert (
        client.post(
            "/api/login",
            headers={"Origin": "https://evil.example"},
            json={"password": "test-password"},
        ).status_code
        == 403
    )
    assert client.post("/internal/claim", json={"room": "x"}).status_code == 401
    assert (
        client.post("/api/login", json={"password": "test-password"}).status_code == 200
    )
    assert client.post("/internal/claim", json={"room": "x"}).status_code == 401


def test_composition_validation_and_active(client):
    c = deepcopy(DEFAULT)
    c["name"] = "Composition de test"
    r = client.post("/api/compositions", json=c)
    assert r.status_code == 200, r.text
    key = r.json()["id"]
    assert client.post("/api/compositions/" + key + "/activate").status_code == 200
    assert client.get("/api/compositions").json()["active"]["id"] == key
    c["tts"]["params"]["speed"] = 1.8
    assert client.put("/api/compositions/" + key, json=c).status_code == 422
    c = deepcopy(DEFAULT)
    c["llm"]["raw"] = {"api_key": "leak"}
    assert client.post("/api/compositions", json=c).status_code == 422
    c = deepcopy(DEFAULT)
    c["realtime"]["model"] = "inconnu"
    c["mode"] = "realtime"
    assert client.post("/api/compositions", json=c).status_code == 422


def test_encrypted_key_no_readback(client):
    secret = "secret-not-for-the-browser-1234"
    assert client.put("/api/keys/soniox", json={"key": secret}).status_code == 200
    response = client.get("/api/keys")
    assert secret not in response.text
    item = next(x for x in response.json() if x["provider"] == "soniox")
    assert item["suffix"] == "1234"
    with db() as s:
        value = get(s, "key:soniox")
        assert secret not in str(value)
    assert client.delete("/api/keys/soniox").status_code == 200


def test_snapshot_telemetry_notes_and_claim_idempotency(client):
    with db() as s:
        r = new_run(s, deepcopy(DEFAULT), "web")
    key = r["id"]
    claim = client.post(
        "/internal/claim", headers=WORKER, json={"run_id": key, "room": r["room"]}
    )
    assert claim.status_code == 200, claim.text
    assert claim.json()["credentials"]["tts"]["key"] == "env-cartesia-test"
    assert (
        client.post(
            "/internal/claim", headers=WORKER, json={"run_id": key, "room": r["room"]}
        ).status_code
        == 409
    )
    assert (
        client.put(
            "/api/runs/" + key + "/rating", json={"rating": 4, "comment": "Naturel"}
        ).status_code
        == 200
    )
    payload = {
        "status": "completed",
        "duration": 60,
        "usage": {
            "llm:groq:openai/gpt-oss-20b": {"input_tokens": 1000, "output_tokens": 100}
        },
        "turns": [{"latency_ms": 500}, {"latency_ms": 900}],
        "transcript": [{"role": "user", "text": "Bonjour"}],
    }
    assert (
        client.put("/internal/runs/" + key, headers=WORKER, json=payload).status_code
        == 200
    )
    done = client.get("/api/runs/" + key).json()
    assert done["rating"] == 4
    assert done["median_ms"] == 700
    client.put(
        "/api/prices",
        json={
            "id": "llm:groq:openai/gpt-oss-20b",
            "currency": "EUR",
            "rates": {"input_tokens": 1, "output_tokens": 1},
            "source": "manual",
        },
    )
    client.put("/internal/runs/" + key, headers=WORKER, json=payload)
    assert client.get("/api/runs/" + key).json()["cost"] == done["cost"]
    assert any(
        x["id"] == done["composition_version"]
        for x in client.get("/api/compare").json()
    )
    # A late running heartbeat cannot regress a terminal run.
    client.put(
        "/internal/runs/" + key, headers=WORKER, json={**payload, "status": "running"}
    )
    assert client.get("/api/runs/" + key).json()["status"] == "completed"
    assert (
        client.put("/api/runs/" + key + "/rating", json={"rating": 6}).status_code
        == 422
    )


def test_negative_usage_and_audio_auth(client):
    assert (
        client.put(
            "/internal/runs/nope",
            headers=WORKER,
            json={
                "status": "running",
                "duration": 1,
                "usage": {"tts": {"characters": -1}},
            },
        ).status_code
        == 422
    )
    client.cookies.clear()
    assert client.get("/api/runs/nope/audio").status_code == 401


def test_quota_is_checked_before_creating_trial(client, monkeypatch):
    import pytest
    from fastapi import HTTPException

    monkeypatch.setenv("MONTHLY_MINUTES_LIMIT", "0")
    with pytest.raises(HTTPException) as error:
        with db() as s:
            new_run(s, deepcopy(DEFAULT), "web")
    assert error.value.status_code == 409
