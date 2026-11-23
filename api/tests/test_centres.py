import pytest


@pytest.fixture
def seeded_client(client):
    from app import seed_centres
    seed_centres()
    return client


def test_list_centres(seeded_client):
    r = seeded_client.get("/api/centres")
    assert r.status_code == 200
    assert len(r.get_json()) == 3


def test_centre_has_expected_fields(seeded_client):
    centre = seeded_client.get("/api/centres/1").get_json()
    expected = {"id", "name", "area", "capacity", "opening_hours", "status"}
    assert expected <= centre.keys()
    assert centre["status"] == "open"


def test_get_centre_not_found(seeded_client):
    r = seeded_client.get("/api/centres/999")
    assert r.status_code == 404
    assert r.get_json() == {"error": "Centre not found"}