"""HTTP client for the Heat Shield Flask REST API.

All network calls live here so views stay clean and the backend URL
is controlled via settings.HEATSHIELD_API_URL.
"""
import requests
from django.conf import settings

TIMEOUT_SECONDS = 5


class ApiError(Exception):
    """Raised when the Flask API is unreachable or returns an error status."""

    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


def _call(method, path, **kwargs):
    url = f"{settings.HEATSHIELD_API_URL}{path}"
    try:
        response = requests.request(method, url, timeout=TIMEOUT_SECONDS, **kwargs)
    except requests.RequestException as exc:
        raise ApiError("The Heat Shield Flask API is offline or unreachable.") from exc

    try:
        body = response.json()
    except ValueError:
        raise ApiError("The API returned an unexpected non-JSON response.", response.status_code)

    if not response.ok:
        message = body.get("error", "Request failed") if isinstance(body, dict) else "Request failed"
        raise ApiError(message, response.status_code)
    return body


def list_requests(**filters):
    return _call("GET", "/requests", params=filters)


def create_request(payload):
    return _call("POST", "/requests", json=payload)


def update_request(request_id, payload):
    return _call("PATCH", f"/requests/{request_id}", json=payload)


def list_centres(**filters):
    return _call("GET", "/centres", params=filters)


def list_bookings(**filters):
    return _call("GET", "/bookings", params=filters)


def create_booking(payload):
    return _call("POST", "/bookings", json=payload)


def update_booking(booking_id, payload):
    return _call("PATCH", f"/bookings/{booking_id}", json=payload)