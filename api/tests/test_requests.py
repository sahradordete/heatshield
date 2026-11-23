def test_health(client):
    assert client.get("/api/health").get_json() == {"status": "ok"}

VALID = {"description": "Needs a cool place (fictional)", "category": "cooling_space", "area": "Bolton"}


def test_create_request_ok(client):
    assert client.post("/api/requests", json=VALID).status_code == 201


def test_create_rejects_invalid_category(client):
    r = client.post("/api/requests", json={**VALID, "category": "nonsense"})
    assert r.status_code == 400


def test_create_rejects_invalid_priority(client):
    r = client.post("/api/requests", json={**VALID, "priority": "urgent!!"})
    assert r.status_code == 400


def test_update_rejects_invalid_status(client):
    rid = client.post("/api/requests", json=VALID).get_json()["id"]
    r = client.patch(f"/api/requests/{rid}", json={"status": "banana"})
    assert r.status_code == 400