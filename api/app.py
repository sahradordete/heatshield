"""Heat Shield – COM6402 Sprint 1 starter (ONE FILE).

Learning focus: Flask routes, JSON, SQLAlchemy and simple CRUD.
Only the fictional Support Request entity is implemented.

Install (in a virtual environment):
    python -m pip install flask flask-sqlalchemy
Run:
    python app.py
Try:
    http://127.0.0.1:5000/api/health
    http://127.0.0.1:5000/api/requests

This is a TEACHING EXAMPLE, not a finished Heat Shield application.
There is no authentication: run locally only, using fictional data.
"""
import os

from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

# 1. Set up Flask and the SQLite database.
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///heatshield.db")
db = SQLAlchemy(app)

CATEGORIES = ("cooling_space", "welfare_visit", "practical_assistance")
PRIORITIES = ("low", "medium", "high")
STATUSES = ("new", "in_progress", "completed")
ALLOWED = {"category": CATEGORIES, "priority": PRIORITIES, "status": STATUSES}


# 2. MODEL: a Python class representing a database table.
# MODEL: a cooling centre that residents can be booked into.
class SupportRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    area = db.Column(db.String(80), nullable=False)
    priority = db.Column(db.String(20), nullable=False, default="medium")
    status = db.Column(db.String(20), nullable=False, default="new")
    booking = db.relationship("Booking", back_populates="support_request", uselist=False)

    def to_dict(self):
        return {
            "id": self.id,
            "description": self.description,
            "category": self.category,
            "area": self.area,
            "priority": self.priority,
            "status": self.status,
        }
class CoolingCentre(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    area = db.Column(db.String(80), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    opening_hours = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="open")
    bookings = db.relationship("Booking", back_populates="cooling_centre", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "area": self.area,
            "capacity": self.capacity,
            "opening_hours": self.opening_hours,
            "status": self.status,
        }

# Booking Class
class Booking(db.Model):
    booking_id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(
        db.Integer, db.ForeignKey("support_request.id"), nullable=True, unique=True
    )
    centre_id = db.Column(
        db.Integer, db.ForeignKey("cooling_centre.id"), nullable=False
    )
    booking_date = db.Column(db.Date, nullable=False)
    booking_time = db.Column(db.String(50), nullable=False)
    spaces_required = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(20), nullable=False, default="Confirmed")

    # ORM Relationships
    support_request = db.relationship("SupportRequest", back_populates="booking")
    cooling_centre = db.relationship("CoolingCentre", back_populates="bookings")

    def to_dict(self):
        return {
            "booking_id": self.booking_id,
            "request_id": self.request_id,
            "centre_id": self.centre_id,
            "booking_date": self.booking_date.isoformat() if self.booking_date else None,
            "booking_time": self.booking_time,
            "spaces_required": self.spaces_required,
            "status": self.status,
        }


# Fictional seed data: (name, area, capacity, opening_hours).
SEED_CENTRES = [
    ("Bolton Community Centre", "Bolton", 3, "09:00-17:00"),
    ("Farnworth Library Hall", "Farnworth", 2, "10:00-16:00"),
    ("Horwich Leisure Hall", "Horwich", 4, "09:00-18:00"),
]


def seed_centres():
    """Add the fictional centres, but only if the table is empty."""
    if db.session.scalar(db.select(db.func.count(CoolingCentre.id))) == 0:
        for name, area, capacity, hours in SEED_CENTRES:
            db.session.add(CoolingCentre(name=name, area=area, capacity=capacity,
                                         opening_hours=hours, status="open"))
        db.session.commit()


# 3. HEALTH CHECK: a simple way to check whether Flask is running.
@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


# 4. READ: all requests, optionally filtered by a known field.
@app.get("/api/requests")
def list_requests():
    query = db.select(SupportRequest)

    # Example: GET /api/requests?status=new&area=Bolton
    for field in ("category", "area", "priority", "status"):
        value = request.args.get(field)
        if value:
            query = query.where(getattr(SupportRequest, field) == value)

    records = db.session.scalars(query.order_by(SupportRequest.id)).all()
    return jsonify([record.to_dict() for record in records])


# 5. READ: one request by its ID, or return a 404 error.
@app.get("/api/requests/<int:request_id>")
def get_request(request_id):
    record = db.session.get(SupportRequest, request_id)
    if record is None:
        return jsonify({"error": "Request not found"}), 404
    return jsonify(record.to_dict())


# 6. CREATE: receive JSON, check required fields, and save a new row.
@app.post("/api/requests")
def create_request():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Send a JSON object"}), 400

    required = ("description", "category", "area")
    for field in required:
        if not isinstance(data.get(field), str) or not data[field].strip():
            return jsonify({"error": f"{field} is required"}), 400

    # This simple example accepts two optional fields.
    # Students should improve validation (allowed values, lengths, etc.).
    for field in ("priority", "status"):
        if field in data and (
            not isinstance(data[field], str) or not data[field].strip()
        ):
            return jsonify({"error": f"{field} must be text"}), 400

    for field, allowed in ALLOWED.items():
        value = data.get(field)
        if value is not None and value.strip() not in allowed:
            return jsonify({"error": f"{field} must be one of {list(allowed)}"}), 400

    record = SupportRequest(
        description=data["description"].strip(),
        category=data["category"].strip(),
        area=data["area"].strip(),
        priority=data.get("priority", "medium").strip(),
        status=data.get("status", "new").strip(),
    )
    db.session.add(record)
    db.session.commit()  # Save changes to SQLite.
    return jsonify(record.to_dict()), 201


# 7. UPDATE: PATCH only the fields supplied in the request.
@app.patch("/api/requests/<int:request_id>")
def update_request(request_id):
    record = db.session.get(SupportRequest, request_id)
    if record is None:
        return jsonify({"error": "Request not found"}), 404

    data = request.get_json(silent=True)
    allowed = ("description", "category", "area", "priority", "status")
    if not isinstance(data, dict) or not data:
        return jsonify({"error": "Send fields to update as JSON"}), 400

    for field, value in data.items():
        if field not in allowed:
            return jsonify({"error": f"Cannot update {field}"}), 400
        if not isinstance(value, str) or not value.strip():
            return jsonify({"error": f"{field} must contain text"}), 400
        
        if field in ALLOWED and value.strip() not in ALLOWED[field]:
            return jsonify({"error": f"{field} must be one of {list(ALLOWED[field])}"}), 400
        setattr(record, field, value.strip())

    db.session.commit()
    return jsonify(record.to_dict())


# CENTRES: read all centres, or one centre by ID.
@app.get("/api/centres")
def list_centres():
    records = db.session.scalars(db.select(CoolingCentre).order_by(CoolingCentre.id)).all()
    return jsonify([record.to_dict() for record in records])


@app.get("/api/centres/<int:centre_id>")
def get_centre(centre_id):
    record = db.session.get(CoolingCentre, centre_id)
    if record is None:
        return jsonify({"error": "Centre not found"}), 404
    return jsonify(record.to_dict())

if __name__ == "__main__":
    # Create the table if it does not already exist.
    # Later: consider proper database migrations when changing the schema.
    with app.app_context():
        db.create_all()
        seed_centres()

    # Flask's debug server is only suitable for LOCAL development.
    app.run(debug=True, host="127.0.0.1", port=5000)


# NEXT STEPS FOR STUDENTS:
# - Create Cooling Centre and Booking models and discuss their relationships.
# - Agree JSON fields/endpoints with the Django frontend developer.
# - Add automated tests for success, validation errors and missing records.
# - Produce OpenAPI documentation and explore Swagger UI.
# - Refactor into Models, Views and Controllers (MVC) when the team is ready.
# - Plan authentication, authorisation and audit trails; do not deploy as-is.
