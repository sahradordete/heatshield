from django.shortcuts import render, redirect

# Mock data simulating the Flask API response until integration
MOCK_REQUESTS = [
    {
        "request_id": 1,
        "description": "Elderly resident without air conditioning needs welfare check.",
        "category": "Welfare",
        "priority": "High",
        "area": "Bolton",
        "status": "In Progress",
        "created_at": "2026-11-23 09:00",
    },
    {
        "request_id": 2,
        "description": "Family of 3 requesting cooling space for the afternoon.",
        "category": "Cooling Space",
        "priority": "Medium",
        "area": "Farnworth",
        "status": "New",
        "created_at": "2026-11-23 10:15",
    },
]

MOCK_CENTRES = [
    {"centre_id": 1, "name": "Bolton Community Centre", "area": "Bolton", "capacity": 50, "opening_hours": "08:00 - 20:00", "status": "Open"},
    {"centre_id": 2, "name": "Farnworth Leisure Hub", "area": "Farnworth", "capacity": 30, "opening_hours": "09:00 - 19:00", "status": "Open"},
]

def index(request):
    if request.method == 'POST':
        description = request.POST.get('description', '').strip()
        if description:
            MOCK_REQUESTS.insert(0, {
                "request_id": len(MOCK_REQUESTS) + 1,
                "description": description,
                "category": request.POST.get('category', 'Welfare'),
                "priority": request.POST.get('priority', 'Medium'),
                "area": request.POST.get('area', 'Bolton'),
                "status": "New",
                "created_at": "Just now",
            })
        return redirect('dashboard_index')

    return render(request, 'dashboard/index.html', {
        'requests': MOCK_REQUESTS,
        'centres': MOCK_CENTRES,
    })