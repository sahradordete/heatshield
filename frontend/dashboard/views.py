from datetime import date

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, render

from . import api_client
from .api_client import ApiError

# Values accepted by the Flask API contract (/apidocs).
CATEGORIES = ["Welfare", "Cooling Space", "Practical Assistance"]
PRIORITIES = [("low", "Low"), ("medium", "Medium"), ("high", "High")]
AREAS = ["Bolton", "Farnworth", "Horwich"]
STATUSES = [("new", "New"), ("in_progress", "In Progress"), ("completed", "Completed")]
BOOKING_TIMES = ["09:00-13:00", "13:00-17:00", "09:00-17:00"]


def _display_time(value):
    """Format ISO timestamp '2026-11-26T10:15:00.123456' -> '2026-11-26 10:15'."""
    return value[:16].replace("T", " ") if value else ""


def index(request):
    if request.method == "POST":
        action = request.POST.get("action", "create")

        if action == "update_status":
            try:
                req_id = int(request.POST.get("request_id", 0))
            except ValueError:
                messages.error(request, "Invalid support request ID.")
                return redirect("dashboard_index")

            new_status = request.POST.get("status", "new")
            try:
                api_client.update_request(req_id, {"status": new_status})
                messages.success(request, f"Request #{req_id} status updated to {new_status}.")
            except ApiError as exc:
                messages.error(request, f"Could not update request #{req_id}: {exc}")
            return redirect("dashboard_index")

        if action == "create_booking":
            try:
                req_id = int(request.POST.get("request_id", 0))
                centre_id = int(request.POST.get("centre_id", 0))
                spaces = int(request.POST.get("spaces_required", 1))
            except ValueError:
                messages.error(request, "Invalid booking parameters.")
                return redirect("dashboard_index")

            booking_date = request.POST.get("booking_date", "").strip()
            booking_time = request.POST.get("booking_time", "").strip()
            payload = {
                "request_id": req_id,
                "centre_id": centre_id,
                "booking_date": booking_date,
                "booking_time": booking_time,
                "spaces_required": spaces,
            }
            try:
                created = api_client.create_booking(payload)
                messages.success(
                    request,
                    f"Booking #{created.get('booking_id')} confirmed for Request #{req_id}.",
                )
            except ApiError as exc:
                messages.error(request, f"Booking rejected: {exc}")
            return redirect("dashboard_index")

        if action == "update_booking":
            try:
                booking_id = int(request.POST.get("booking_id", 0))
            except ValueError:
                messages.error(request, "Invalid booking ID.")
                return redirect("dashboard_index")

            new_status = request.POST.get("status", "Cancelled")
            try:
                api_client.update_booking(booking_id, {"status": new_status})
                messages.success(request, f"Booking #{booking_id} marked as {new_status}.")
            except ApiError as exc:
                messages.error(request, f"Could not update booking #{booking_id}: {exc}")
            return redirect("dashboard_index")

        # Default action: create support request
        payload = {
            "description": request.POST.get("description", "").strip(),
            "category": request.POST.get("category"),
            "priority": request.POST.get("priority"),
            "area": request.POST.get("area"),
        }
        if not payload["description"]:
            messages.error(request, "Description is required.")
            return redirect("dashboard_index")

        try:
            created = api_client.create_request(payload)
            messages.success(request, f"Support request #{created.get('request_id', '')} created.")
        except ApiError as exc:
            messages.error(request, f"Could not create request: {exc}")
        return redirect("dashboard_index")

    api_connected = False
    api_error = ""
    support_requests = []
    centres = []
    bookings = []

    try:
        support_requests = api_client.list_requests()
        centres = api_client.list_centres()
        bookings = api_client.list_bookings()
        api_connected = True
    except ApiError as exc:
        api_error = str(exc)

    centres_by_id = {c["centre_id"]: c for c in centres}
    bookings_by_request = {b["request_id"]: b for b in bookings}

    confirmed_spaces_by_centre = {}
    for b in bookings:
        if b.get("status") == "Confirmed":
            cid = b.get("centre_id")
            confirmed_spaces_by_centre[cid] = confirmed_spaces_by_centre.get(cid, 0) + b.get("spaces_required", 1)
        b["centre_name"] = centres_by_id.get(b.get("centre_id"), {}).get("name", f"Centre #{b.get('centre_id')}")

    for centre in centres:
        booked = confirmed_spaces_by_centre.get(centre["centre_id"], 0)
        centre["booked_spaces"] = booked
        centre["available_spaces"] = max(0, centre.get("capacity", 0) - booked)

    for item in support_requests:
        item["created_at"] = _display_time(item.get("created_at"))
        item["booking"] = bookings_by_request.get(item["request_id"])

    total_count = len(support_requests)
    outstanding_count = sum(1 for r in support_requests if r.get("status") != "completed")
    completed_count = sum(1 for r in support_requests if r.get("status") == "completed")
    confirmed_bookings_count = sum(1 for b in bookings if b.get("status") == "Confirmed")

    query = request.GET.get("q", "").strip()
    selected_category = request.GET.get("category", "")
    selected_priority = request.GET.get("priority", "")
    selected_area = request.GET.get("area", "")
    selected_status = request.GET.get("status", "")

    filtered_requests = support_requests
    if query:
        filtered_requests = [
            r for r in filtered_requests if query.lower() in r.get("description", "").lower()
        ]
    if selected_category:
        filtered_requests = [
            r for r in filtered_requests if r.get("category") == selected_category
        ]
    if selected_priority:
        filtered_requests = [
            r for r in filtered_requests if r.get("priority") == selected_priority
        ]
    if selected_area:
        filtered_requests = [
            r for r in filtered_requests if r.get("area") == selected_area
        ]
    if selected_status:
        filtered_requests = [
            r for r in filtered_requests if r.get("status") == selected_status
        ]

    bookable_requests = [
        r for r in support_requests
        if r.get("status") != "completed"
        and (r.get("booking") is None or r["booking"].get("status") != "Confirmed")
    ]
    open_centres = [c for c in centres if c.get("status") == "open"]

    return render(
        request,
        "dashboard/index.html",
        {
            "requests": filtered_requests,
            "bookable_requests": bookable_requests,
            "centres": centres,
            "open_centres": open_centres,
            "bookings": bookings,
            "api_connected": api_connected,
            "api_error": api_error,
            "api_url": settings.HEATSHIELD_API_URL,
            "total_count": total_count,
            "outstanding_count": outstanding_count,
            "completed_count": completed_count,
            "confirmed_bookings_count": confirmed_bookings_count,
            "categories": CATEGORIES,
            "priorities": PRIORITIES,
            "areas": AREAS,
            "statuses": STATUSES,
            "booking_times": BOOKING_TIMES,
            "today_iso": date.today().isoformat(),
            "filters": {
                "q": query,
                "category": selected_category,
                "priority": selected_priority,
                "area": selected_area,
                "status": selected_status,
            },
        },
    )