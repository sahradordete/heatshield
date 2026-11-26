import json
from datetime import datetime
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.shortcuts import redirect, render

FLASK_API_BASE = "http://127.0.0.1:5000/api"

MOCK_REQUESTS = [
    {
        "request_id": 1,
        "description": "Elderly resident without fan or air conditioning needs welfare check.",
        "category": "Welfare",
        "priority": "High",
        "area": "Bolton",
        "status": "New",
        "created_at": "2026-11-26 09:15",
    },
    {
        "request_id": 2,
        "description": "Practical assistance needed to reach cooling centre during peak heat.",
        "category": "Practical Assistance",
        "priority": "Medium",
        "area": "Farnworth",
        "status": "In Progress",
        "created_at": "2026-11-26 10:00",
    },
    {
        "request_id": 3,
        "description": "Afternoon cooling space seat requested for vulnerable resident.",
        "category": "Cooling Space",
        "priority": "Low",
        "area": "Horwich",
        "status": "Completed",
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
        "status": "Open",
    },
    {
        "centre_id": 2,
        "name": "Farnworth Leisure Hub",
        "area": "Farnworth",
        "capacity": 25,
        "opening_hours": "09:00 - 19:00",
        "status": "Open",
    },
    {
        "centre_id": 3,
        "name": "Horwich Library",
        "area": "Horwich",
        "capacity": 15,
        "opening_hours": "09:00 - 17:00",
        "status": "Closed",
    },
]


def _fetch_json(endpoint, timeout=1.5):
    req = Request(f"{FLASK_API_BASE}{endpoint}", headers={"Accept": "application/json"})
    with urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _send_json(endpoint, payload, method="POST", timeout=1.5):
    data = json.dumps(payload).encode("utf-8")
    req = Request(
        f"{FLASK_API_BASE}{endpoint}",
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method=method,
    )
    with urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def index(request):
    api_connected = False

    if request.method == "POST":
        action = request.POST.get("action", "create")

        if action == "update_status":
            try:
                req_id = int(request.POST.get("request_id", 0))
            except ValueError:
                return redirect(request.path)
            new_status = request.POST.get("status", "New")
            try:
                _send_json(f"/requests/{req_id}", {"status": new_status}, method="PATCH")
            except (URLError, TimeoutError, OSError, ValueError):
                for item in MOCK_REQUESTS:
                    if item["request_id"] == req_id:
                        item["status"] = new_status
                        break
            return redirect(request.path)

        description = request.POST.get("description", "").strip()
        category = request.POST.get("category", "Welfare")
        priority = request.POST.get("priority", "Medium")
        area = request.POST.get("area", "Bolton")

        if description:
            payload = {
                "description": description,
                "category": category,
                "priority": priority,
                "area": area,
                "status": "New",
            }
            try:
                _send_json("/requests", payload, method="POST")
            except (URLError, TimeoutError, OSError, ValueError):
                next_id = max((r["request_id"] for r in MOCK_REQUESTS), default=0) + 1
                MOCK_REQUESTS.insert(
                    0,
                    {
                        "request_id": next_id,
                        **payload,
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    },
                )
        return redirect(request.path)

    try:
        requests_data = _fetch_json("/requests")
        centres_data = _fetch_json("/centres")
        api_connected = True
    except (URLError, TimeoutError, OSError, ValueError):
        requests_data = list(MOCK_REQUESTS)
        centres_data = list(MOCK_CENTRES)

    outstanding_count = sum(1 for r in requests_data if r.get("status") != "Completed")
    completed_count = sum(1 for r in requests_data if r.get("status") == "Completed")

    query = request.GET.get("q", "").strip()
    selected_category = request.GET.get("category", "")
    selected_priority = request.GET.get("priority", "")
    selected_area = request.GET.get("area", "")
    selected_status = request.GET.get("status", "")

    filtered_requests = requests_data
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

    context = {
        "requests": filtered_requests,
        "centres": centres_data,
        "api_connected": api_connected,
        "outstanding_count": outstanding_count,
        "completed_count": completed_count,
        "filters": {
            "q": query,
            "category": selected_category,
            "priority": selected_priority,
            "area": selected_area,
            "status": selected_status,
        },
    }
    return render(request, "dashboard/index.html", context)
