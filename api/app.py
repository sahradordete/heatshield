"""Heat Shield – COM6402 Sprint 1 Complete Single-File REST API.

Includes:
- SQLAlchemy ORM models (SupportRequest, CoolingCentre, Booking) with modelname_id keys
- CRUD endpoints with validation and capacity checks
- Global JSON error handlers and CORS for Django frontend integration
- Interactive OpenAPI / Swagger UI documentation at /apidocs
"""

from datetime import date, datetime, timezone
import os

from flasgger import Swagger
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

# 1. APP, SWAGGER & DATABASE CONFIGURATION
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///heatshield.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/apidocs",
}

swagger_template = {
    "info": {
        "title": "Heat Shield REST API",
        "description": "Sprint 1 API for managing Support Requests, Cooling Centres, and Bookings.",
        "version": "1.0.0",
    }
}

swagger = Swagger(app, config=swagger_config, template=swagger_template)

# 2. DOMAIN CONSTANTS
CATEGORIES = ("Welfare", "Cooling Space", "Practical Assistance")
PRIORITIES = ("low", "medium", "high")
REQUEST_STATUSES = ("new", "in_progress", "completed")
CENTRE_STATUSES = ("open", "closed")
BOOKING_STATUSES = ("Confirmed", "Cancelled")

ALLOWED_REQUEST_FIELDS = {
    "category": CATEGORIES,
    "priority": PRIORITIES,
    "status": REQUEST_STATUSES,
}


# 3. DATABASE MODELS
class SupportRequest(db.Model):
    __tablename__ = "support_request"

    request_id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    area = db.Column(db.String(80), nullable=False)
    priority = db.Column(db.String(20), nullable=False, default="medium")
    status = db.Column(db.String(20), nullable=False, default="new")
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    booking = db.relationship(
        "Booking", back_populates="support_request", uselist=False
    )

    def to_dict(self):
        return {
            "request_id": self.request_id,
            "description": self.description,
            "category": self.category,
            "area": self.area,
            "priority": self.priority,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class CoolingCentre(db.Model):
    __tablename__ = "cooling_centre"

    centre_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    area = db.Column(db.String(80), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    opening_hours = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="open")

    bookings = db.relationship("Booking", back_populates="cooling_centre", lazy=True)

    def to_dict(self):
        return {
            "centre_id": self.centre_id,
            "name": self.name,
            "area": self.area,
            "capacity": self.capacity,
            "opening_hours": self.opening_hours,
            "status": self.status,
        }


class Booking(db.Model):
    __tablename__ = "booking"

    booking_id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(
        db.Integer,
        db.ForeignKey("support_request.request_id"),
        nullable=False,
        unique=True,
    )
    centre_id = db.Column(
        db.Integer, db.ForeignKey("cooling_centre.centre_id"), nullable=False
    )
    booking_date = db.Column(db.Date, nullable=False)
    booking_time = db.Column(db.String(50), nullable=False)
    spaces_required = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(20), nullable=False, default="Confirmed")

    support_request = db.relationship("SupportRequest", back_populates="booking")
    cooling_centre = db.relationship("CoolingCentre", back_populates="bookings")

    def to_dict(self):
        return {
            "booking_id": self.booking_id,
            "request_id": self.request_id,
            "centre_id": self.centre_id,
            "booking_date": (
                self.booking_date.isoformat() if self.booking_date else None
            ),
            "booking_time": self.booking_time,
            "spaces_required": self.spaces_required,
            "status": self.status,
        }


# 4. SEED DATA
SEED_CENTRES = [
    ("Bolton Community Centre", "Bolton", 3, "09:00-17:00"),
    ("Farnworth Library Hall", "Farnworth", 2, "10:00-16:00"),
    ("Horwich Leisure Hall", "Horwich", 4, "09:00-18:00"),
]


def seed_centres():
    """Populate initial cooling centres if the table is empty."""
    if db.session.scalar(db.select(db.func.count(CoolingCentre.centre_id))) == 0:
        for name, area, capacity, hours in SEED_CENTRES:
            db.session.add(
                CoolingCentre(
                    name=name,
                    area=area,
                    capacity=capacity,
                    opening_hours=hours,
                    status="open",
                )
            )
        db.session.commit()


# 5. GLOBAL JSON ERROR HANDLERS (Ensures Django always receives JSON, never HTML)
@app.errorhandler(400)
def bad_request(error):
    return jsonify({"error": "Bad request"}), 400


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Resource not found"}), 404


@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"error": "Method not allowed"}), 405


@app.errorhandler(500)
def internal_server_error(error):
    db.session.rollback()
    return jsonify({"error": "Internal server error"}), 500


# 6. HEALTH CHECK ENDPOINT
@app.get("/api/health")
def health():
    """Health check endpoint
    ---
    tags:
      - System
    responses:
      200:
        description: API is running
    """
    return jsonify({"status": "ok"}), 200


# 7. SUPPORT REQUESTS ENDPOINTS
@app.get("/api/requests")
def list_requests():
    """Retrieve all support requests (with optional filters)
    ---
    tags:
      - Support Requests
    parameters:
      - name: category
        in: query
        type: string
        enum: ["Welfare", "Cooling Space", "Practical Assistance"]
      - name: area
        in: query
        type: string
      - name: priority
        in: query
        type: string
        enum: ["low", "medium", "high"]
      - name: status
        in: query
        type: string
        enum: ["new", "in_progress", "completed"]
    responses:
      200:
        description: List of support requests
    """
    query = db.select(SupportRequest)

    for field in ("category", "area", "priority", "status"):
        value = request.args.get(field)
        if value:
            query = query.where(getattr(SupportRequest, field) == value)

    records = db.session.scalars(query.order_by(SupportRequest.request_id)).all()
    return jsonify([record.to_dict() for record in records]), 200


@app.get("/api/requests/<int:request_id>")
def get_request(request_id):
    """Retrieve a single support request by ID
    ---
    tags:
      - Support Requests
    parameters:
      - name: request_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Support request details
      404:
        description: Request not found
    """
    record = db.session.get(SupportRequest, request_id)
    if record is None:
        return jsonify({"error": "Request not found"}), 404
    return jsonify(record.to_dict()), 200


@app.post("/api/requests")
def create_request():
    """Create a new support request
    ---
    tags:
      - Support Requests
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - description
            - category
            - area
          properties:
            description:
              type: string
              example: Elderly resident requires transport to a cooling centre
            category:
              type: string
              enum: ["Welfare", "Cooling Space", "Practical Assistance"]
              example: Cooling Space
            area:
              type: string
              example: Bolton
            priority:
              type: string
              enum: ["low", "medium", "high"]
              default: medium
            status:
              type: string
              enum: ["new", "in_progress", "completed"]
              default: new
    responses:
      201:
        description: Support request created
      400:
        description: Validation error
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Send a JSON object"}), 400

    required = ("description", "category", "area")
    for field in required:
        if not isinstance(data.get(field), str) or not data[field].strip():
            return jsonify({"error": f"{field} is required"}), 400

    for field in ("priority", "status"):
        if field in data and (
            not isinstance(data[field], str) or not data[field].strip()
        ):
            return jsonify({"error": f"{field} must be text"}), 400

    for field, allowed in ALLOWED_REQUEST_FIELDS.items():
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
    db.session.commit()
    return jsonify(record.to_dict()), 201


@app.patch("/api/requests/<int:request_id>")
def update_request(request_id):
    """Partially update an existing support request
    ---
    tags:
      - Support Requests
    parameters:
      - name: request_id
        in: path
        type: integer
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            description:
              type: string
            category:
              type: string
              enum: ["Welfare", "Cooling Space", "Practical Assistance"]
            area:
              type: string
            priority:
              type: string
              enum: ["low", "medium", "high"]
            status:
              type: string
              enum: ["new", "in_progress", "completed"]
    responses:
      200:
        description: Support request updated
      400:
        description: Validation error
      404:
        description: Request not found
    """
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

        if (
            field in ALLOWED_REQUEST_FIELDS
            and value.strip() not in ALLOWED_REQUEST_FIELDS[field]
        ):
            return (
                jsonify(
                    {
                        "error": f"{field} must be one of {list(ALLOWED_REQUEST_FIELDS[field])}"
                    }
                ),
                400,
            )
        setattr(record, field, value.strip())

    db.session.commit()
    return jsonify(record.to_dict()), 200


# 8. COOLING CENTRES ENDPOINTS
@app.get("/api/centres")
def list_centres():
    """Retrieve all cooling centres (with optional filters)
    ---
    tags:
      - Cooling Centres
    parameters:
      - name: area
        in: query
        type: string
      - name: status
        in: query
        type: string
        enum: ["open", "closed"]
    responses:
      200:
        description: List of cooling centres
    """
    query = db.select(CoolingCentre)

    for field in ("area", "status"):
        value = request.args.get(field)
        if value:
            query = query.where(getattr(CoolingCentre, field) == value)

    records = db.session.scalars(query.order_by(CoolingCentre.centre_id)).all()
    return jsonify([record.to_dict() for record in records]), 200


@app.get("/api/centres/<int:centre_id>")
def get_centre(centre_id):
    """Retrieve a single cooling centre by ID
    ---
    tags:
      - Cooling Centres
    parameters:
      - name: centre_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Cooling centre details
      404:
        description: Centre not found
    """
    record = db.session.get(CoolingCentre, centre_id)
    if record is None:
        return jsonify({"error": "Centre not found"}), 404
    return jsonify(record.to_dict()), 200


# 9. BOOKINGS ENDPOINTS
@app.get("/api/bookings")
def list_bookings():
    """Retrieve all bookings (with optional filters)
    ---
    tags:
      - Bookings
    parameters:
      - name: centre_id
        in: query
        type: integer
      - name: status
        in: query
        type: string
        enum: ["Confirmed", "Cancelled"]
    responses:
      200:
        description: List of bookings
    """
    query = db.select(Booking)

    centre_id = request.args.get("centre_id", type=int)
    if centre_id is not None:
        query = query.where(Booking.centre_id == centre_id)

    status = request.args.get("status")
    if status:
        query = query.where(Booking.status == status)

    records = db.session.scalars(query.order_by(Booking.booking_id)).all()
    return jsonify([record.to_dict() for record in records]), 200


@app.get("/api/bookings/<int:booking_id>")
def get_booking(booking_id):
    """Retrieve a single booking by ID
    ---
    tags:
      - Bookings
    parameters:
      - name: booking_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Booking details
      404:
        description: Booking not found
    """
    record = db.session.get(Booking, booking_id)
    if record is None:
        return jsonify({"error": "Booking not found"}), 404
    return jsonify(record.to_dict()), 200


@app.post("/api/bookings")
def create_booking():
    """Create a new cooling centre booking (subject to availability and capacity)
    ---
    tags:
      - Bookings
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - request_id
            - centre_id
            - booking_date
            - booking_time
          properties:
            request_id:
              type: integer
              example: 1
            centre_id:
              type: integer
              example: 1
            booking_date:
              type: string
              format: date
              example: "2026-11-26"
            booking_time:
              type: string
              example: "09:00-17:00"
            spaces_required:
              type: integer
              default: 1
              example: 1
    responses:
      201:
        description: Booking confirmed
      400:
        description: Validation error
      404:
        description: Support request or cooling centre not found
      409:
        description: Duplicate booking, centre closed or insufficient capacity
    """

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Send a JSON object"}), 400

    for field in ("request_id", "centre_id", "booking_date", "booking_time"):
        if field not in data:
            return jsonify({"error": f"{field} is required"}), 400

    if not is_int(data["request_id"]) or not is_int(data["centre_id"]):
        return jsonify({"error": "request_id and centre_id must be integers"}), 400

    if not isinstance(data["booking_time"], str) or not data["booking_time"].strip():
        return jsonify({"error": "booking_time must be text"}), 400

    try:
        parsed_date = date.fromisoformat(str(data["booking_date"]))
    except ValueError:
        return jsonify({"error": "booking_date must be YYYY-MM-DD"}), 400

    spaces = data.get("spaces_required", 1)
    if not isinstance(spaces, int) or isinstance(spaces, bool) or spaces < 1:
        return jsonify({"error": "spaces_required must be a positive integer"}), 400

    support_req = db.session.get(SupportRequest, data["request_id"])
    if support_req is None:
        return jsonify({"error": "Support request not found"}), 404
    existing = support_req.booking
    if existing is not None and existing.status == "Confirmed":
        return jsonify({"error": "Support request already has an active booking"}), 409

    centre = db.session.get(CoolingCentre, data["centre_id"])
    if centre is None:
        return jsonify({"error": "Cooling centre not found"}), 404

    booking_time = data["booking_time"].strip()
    problem = check_centre_can_take(centre, parsed_date, booking_time, spaces)
    if problem:
        return jsonify(problem[0]), problem[1]

    if existing is not None:
        # The request's earlier booking was cancelled: reuse that row
        # (request_id is unique, so a second row would be rejected).
        existing.centre_id = centre.centre_id
        existing.booking_date = parsed_date
        existing.booking_time = booking_time
        existing.spaces_required = spaces
        existing.status = "Confirmed"
        booking = existing
    else:
        booking = Booking(
            request_id=support_req.request_id,
            centre_id=centre.centre_id,
            booking_date=parsed_date,
            booking_time=booking_time,
            spaces_required=spaces,
            status="Confirmed",
        )
        db.session.add(booking)
    db.session.commit()
    return jsonify(booking.to_dict()), 201

  
@app.patch("/api/bookings/<int:booking_id>")
def update_booking(booking_id):
    """Update a booking status (e.g., cancel a booking)
    ---
    tags:
      - Bookings
    parameters:
      - name: booking_id
        in: path
        type: integer
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - status
          properties:
            status:
              type: string
              enum: ["Confirmed", "Cancelled"]
    responses:
      200:
        description: Booking updated
      400:
        description: Invalid status
      404:
        description: Booking not found
      409:
        description: Centre closed or full (when re-confirming a booking)
    """
    booking = db.session.get(Booking, booking_id)
    if booking is None:
        return jsonify({"error": "Booking not found"}), 404

    data = request.get_json(silent=True)
    if not isinstance(data, dict) or data.get("status") not in BOOKING_STATUSES:
        return (
            jsonify({"error": f"status must be one of {list(BOOKING_STATUSES)}"}),
            400,
        )

    if data["status"] == "Confirmed" and booking.status != "Confirmed":
        problem = check_centre_can_take(
            booking.cooling_centre,
            booking.booking_date,
            booking.booking_time,
            booking.spaces_required,
            exclude_booking_id=booking.booking_id,
        )
        if problem:
            return jsonify(problem[0]), problem[1]

    booking.status = data["status"]
    db.session.commit()
    return jsonify(booking.to_dict()), 200


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_centres()

    app.run(debug=True, host=os.environ.get("FLASK_HOST", "0.0.0.0"), port=5000)


def is_int(value):
    """True for real integers only (Python treats True/False as ints)."""
    return isinstance(value, int) and not isinstance(value, bool)


def check_centre_can_take(
    centre, booking_date, booking_time, spaces, exclude_booking_id=None
):
    """Return (error_body, status_code) if the centre cannot take the booking,
    or None if it can. Used by POST /bookings, PATCH /bookings and, in Sprint 2,
    manual reassignment."""
    if centre.status != "open":
        return {"error": "Cooling centre is currently closed"}, 409

    query = db.select(db.func.coalesce(db.func.sum(Booking.spaces_required), 0)).where(
        Booking.centre_id == centre.centre_id,
        Booking.booking_date == booking_date,
        Booking.booking_time == booking_time,
        Booking.status == "Confirmed",
    )
    if exclude_booking_id is not None:
        query = query.where(Booking.booking_id != exclude_booking_id)
    booked_spaces = db.session.scalar(query)

    if booked_spaces + spaces > centre.capacity:
        return {
            "error": "Not enough capacity available",
            "available_spaces": max(0, centre.capacity - booked_spaces),
        }, 409
    return None
