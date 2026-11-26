from app import db, CoolingCentre


def make_request(client):
    body = {"description": "d", "category": "Cooling Space", "area": "Bolton"}
    return client.post("/api/requests", json=body).get_json()["request_id"]


def book(client, request_id, centre_id=2, date="2026-12-01", time="am"):
    return client.post("/api/bookings", json={
        "request_id": request_id, "centre_id": centre_id,
        "booking_date": date, "booking_time": time})


def test_can_rebook_after_cancelling(seeded_client):
    rid = make_request(seeded_client)
    first = book(seeded_client, rid).get_json()
    seeded_client.patch(f"/api/bookings/{first['booking_id']}", json={"status": "Cancelled"})
    assert book(seeded_client, rid).status_code == 201


def test_cannot_reconfirm_into_a_full_centre(seeded_client):
    first = book(seeded_client, make_request(seeded_client)).get_json()
    seeded_client.patch(f"/api/bookings/{first['booking_id']}", json={"status": "Cancelled"})
    for _ in range(2):  # centre 2 has capacity 2
        assert book(seeded_client, make_request(seeded_client)).status_code == 201
    r = seeded_client.patch(f"/api/bookings/{first['booking_id']}", json={"status": "Confirmed"})
    assert r.status_code == 409


def test_can_reconfirm_when_there_is_space(seeded_client):
    first = book(seeded_client, make_request(seeded_client)).get_json()
    seeded_client.patch(f"/api/bookings/{first['booking_id']}", json={"status": "Cancelled"})
    r = seeded_client.patch(f"/api/bookings/{first['booking_id']}", json={"status": "Confirmed"})
    assert r.status_code == 200


def test_cannot_reconfirm_into_a_closed_centre(seeded_client):
    first = book(seeded_client, make_request(seeded_client)).get_json()
    seeded_client.patch(f"/api/bookings/{first['booking_id']}", json={"status": "Cancelled"})
    db.session.get(CoolingCentre, 2).status = "closed"
    db.session.commit()
    r = seeded_client.patch(f"/api/bookings/{first['booking_id']}", json={"status": "Confirmed"})
    assert r.status_code == 409


def test_closed_centre_rejects_new_booking(seeded_client):
    db.session.get(CoolingCentre, 2).status = "closed"
    db.session.commit()
    assert book(seeded_client, make_request(seeded_client)).status_code == 409


def test_boolean_ids_are_rejected(seeded_client):
    r = seeded_client.post("/api/bookings", json={
        "request_id": True, "centre_id": 1,
        "booking_date": "2026-12-01", "booking_time": "am"})
    assert r.status_code == 400