from datetime import datetime

from django.contrib import messages
from django.shortcuts import redirect, render

from . import api_client
from .api_client import ApiError

# Values the API accepts (see the API contract / Swagger at /apidocs).
CATEGORIES = ["Welfare", "Cooling Space", "Practical Assistance"]
PRIORITIES = [("low", "Low"), ("medium", "Medium"), ("high", "High")]
AREAS = ["Bolton", "Farnworth", "Horwich"]
STATUSES = [("new", "New"), ("in_progress", "In Progress"), ("completed", "Completed")]

MOCK_REQUESTS = [
    {
        "request_id": 1,
        "description": "Elderly resident without fan or air conditioning needs welfare check.",
        "category": "Welfare",
        "priority": "high",
        "area": "Bolton",
        "status": "new",
        "created_at": "2026-11-26 09:15",
    },
    {
        "request_id": 2,
        "description": "Practical assistance needed to reach cooling centre during peak heat.",
        "category": "Practical Assistance",
        "priority": "medium",
        "area": "Farnworth",
        "status": "in_progress",
        "created_at": "2026-11-26 10:00",
    },
    {
        "request_id": 3,
        "description": "Afternoon cooling space seat requested for vulnerable resident.",
        "category": "Cooling Space",
        "priority": "low",
        "area": "Horwich",
        "status": "completed",
        "created_at": "2026-11-25 14:30",
    },
]

MOCK_CENTRES = [
    {
        "centre_id": 1,
        "name": "Bolton Community Centre",
        "area": "Bolton",
        "capacity": 40,
        "opening_hours": "08:00 - 20:00",
        "status": "open",
    },
    {
        "centre_id": 2,
        "name": "Farnworth Leisure Hub",
        "area": "Farnworth",
        "capacity": 25,
        "opening_hours": "09:00 - 19:00",
        "status": "open",
    },
    {
        "centre_id": 3,
        "name": "Horwich Library",
        "area": "Horwich",
        "capacity": 15,
        "opening_hours": "09:00 - 17:00",
        "status": "closed",
    },
]


def _display_time(value):
    """'2026-11-26T10:15:00.123456' -> '2026-11-26 10:15' (UTC)."""
    return value[:16].replace("T", " ") if value else ""


def index(request):
    if request.method == "POST":
        action = request.POST.get("action", "create")

        if action == "update_status":
            try:
                req_id = int(request.POST.get("request_id", 0))
            except ValueError:
                return redirect("dashboard_index")
            new_status = request.POST.get("status", "new")
            try:
                api_client.update_request(req_id, {"status": new_status})
                messages.success(request, f"Request #{req_id} updated.")
            except ApiError as exc:
                if exc.status is None:
                    for item in MOCK_REQUESTS:
                        if item["request_id"] == req_id:
                            item["status"] = new_status
                            break
                else:
                    messages.error(request, f"Could not update request: {exc}")
            return redirect("dashboard_index")

        payload = {
            "description": request.POST.get("description", "").strip(),
            "category": request.POST.get("category"),
            "priority": request.POST.get("priority"),
            "area": request.POST.get("area"),
        }
        if payload["description"]:
            try:
                api_client.create_request(payload)
                messages.success(request, "Support request created.")
            except ApiError as exc:
                if exc.status is None:
                    next_id = max((r["request_id"] for r in MOCK_REQUESTS), default=0) + 1
                    MOCK_REQUESTS.insert(
                        0,
                        {
                            "request_id": next_id,
                            **payload,
                            "status": "new",
                            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        },
                    )
                else:
                    messages.error(request, f"Could not create the request: {exc}")
        return redirect("dashboard_index")

    api_connected = False
    try:
        support_requests = api_client.list_requests()
        for item in support_requests:
            item["created_at"] = _display_time(item.get("created_at"))
        centres = api_client.list_centres()
        api_connected = True
    except ApiError:
        support_requests = [dict(r) for r in MOCK_REQUESTS]
        centres = [dict(c) for c in MOCK_CENTRES]

    outstanding_count = sum(1 for r in support_requests if r.get("status") != "completed")
    completed_count = sum(1 for r in support_requests if r.get("status") == "completed")

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

    return render(
        request,
        "dashboard/index.html",
        {
            "requests": filtered_requests,
            "centres": centres,
            "api_connected": api_connected,
            "outstanding_count": outstanding_count,
            "completed_count": completed_count,
            "categories": CATEGORIES,
            "priorities": PRIORITIES,
            "areas": AREAS,
            "statuses": STATUSES,
            "filters": {
                "q": query,
                "category": selected_category,
                "priority": selected_priority,
                "area": selected_area,
                "status": selected_status,
            },
        },
    )
