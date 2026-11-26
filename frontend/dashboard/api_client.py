"""Small client for the Heat Shield Flask API.

All HTTP calls live here so the views stay simple and the API address
is configured in one place (settings.HEATSHIELD_API_URL).
"""
import requests
from django.conf import settings

TIMEOUT_SECONDS = 5


class ApiError(Exception):
    """The API could not be reached, or it answered with an error."""

    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


def _call(method, path, **kwargs):
    url = f"{settings.HEATSHIELD_API_URL}{path}"
    try:
        response = requests.request(method, url, timeout=TIMEOUT_SECONDS, **kwargs)
    except requests.RequestException as exc:
        raise ApiError("The Heat Shield API is not reachable.") from exc

    try:
        body = response.json()
    except ValueError:
        raise ApiError("The API returned an unexpected response.", response.status_code)

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


def list_centres():
    return _call("GET", "/centres")
