from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from .api_client import ApiError


SAMPLE_REQUESTS = [
    {
        "request_id": 1,
        "description": "Elderly resident needs welfare check",
        "category": "Welfare",
        "priority": "high",
        "area": "Bolton",
        "status": "new",
        "created_at": "2026-11-27T09:15:00.000000",
    },
    {
        "request_id": 2,
        "description": "Transport to cooling centre required",
        "category": "Practical Assistance",
        "priority": "medium",
        "area": "Farnworth",
        "status": "completed",
        "created_at": "2026-11-27T10:00:00.000000",
    },
]

SAMPLE_CENTRES = [
    {
        "centre_id": 1,
        "name": "Bolton Community Centre",
        "area": "Bolton",
        "capacity": 3,
        "opening_hours": "08:00 - 20:00",
        "status": "open",
    },
    {
        "centre_id": 2,
        "name": "Horwich Library",
        "area": "Horwich",
        "capacity": 4,
        "opening_hours": "09:00 - 17:00",
        "status": "closed",
    },
]

SAMPLE_BOOKINGS = [
    {
        "booking_id": 10,
        "request_id": 1,
        "centre_id": 1,
        "booking_date": "2026-11-27",
        "booking_time": "09:00-17:00",
        "spaces_required": 1,
        "status": "Confirmed",
    }
]


class DashboardViewTests(TestCase):
    def setUp(self):
        self.url = reverse("dashboard_index")

    @patch("dashboard.views.api_client.list_requests", side_effect=ApiError("The Heat Shield Flask API is offline or unreachable."))
    def test_renders_offline_alert_without_mock_data_when_api_unreachable(self, _mock_list):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["api_connected"])
        self.assertEqual(response.context["total_count"], 0)
        self.assertContains(response, "Flask API Offline")
        self.assertNotContains(response, "Mock Data Mode")

    @patch("dashboard.views.api_client.list_bookings", return_value=[dict(b) for b in SAMPLE_BOOKINGS])
    @patch("dashboard.views.api_client.list_centres", return_value=[dict(c) for c in SAMPLE_CENTRES])
    @patch("dashboard.views.api_client.list_requests", return_value=[dict(r) for r in SAMPLE_REQUESTS])
    def test_renders_live_api_requests_centres_and_bookings(self, _m_req, _m_cen, _m_book):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["api_connected"])
        self.assertEqual(response.context["total_count"], 2)
        self.assertEqual(response.context["outstanding_count"], 1)
        self.assertEqual(response.context["completed_count"], 1)
        self.assertEqual(response.context["confirmed_bookings_count"], 1)
        self.assertContains(response, "Flask API Connected")
        self.assertContains(response, "Bolton Community Centre")

    @patch("dashboard.views.api_client.list_bookings", return_value=[])
    @patch("dashboard.views.api_client.list_centres", return_value=[dict(c) for c in SAMPLE_CENTRES])
    @patch("dashboard.views.api_client.list_requests", return_value=[dict(r) for r in SAMPLE_REQUESTS])
    def test_filters_by_query_category_priority_area_and_status(self, _m_req, _m_cen, _m_book):
        response = self.client.get(
            self.url,
            {
                "q": "cooling centre",
                "category": "Practical Assistance",
                "priority": "medium",
                "area": "Farnworth",
                "status": "completed",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["requests"]), 1)
        self.assertEqual(response.context["requests"][0]["request_id"], 2)

    @patch("dashboard.views.api_client.create_request", return_value={"request_id": 5})
    def test_create_request_posts_to_flask_api(self, mock_create):
        response = self.client.post(
            self.url,
            {
                "action": "create",
                "description": "Deliver drinking water",
                "category": "Practical Assistance",
                "priority": "high",
                "area": "Bolton",
            },
        )

        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        mock_create.assert_called_once_with(
            {
                "description": "Deliver drinking water",
                "category": "Practical Assistance",
                "priority": "high",
                "area": "Bolton",
            }
        )

    @patch("dashboard.views.api_client.update_request", return_value={"request_id": 1, "status": "completed"})
    def test_update_status_sends_patch_to_flask_api(self, mock_update):
        response = self.client.post(
            self.url,
            {
                "action": "update_status",
                "request_id": "1",
                "status": "completed",
            },
        )

        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        mock_update.assert_called_once_with(1, {"status": "completed"})

    @patch("dashboard.views.api_client.create_booking", return_value={"booking_id": 12})
    def test_create_booking_posts_to_flask_api(self, mock_book):
        response = self.client.post(
            self.url,
            {
                "action": "create_booking",
                "request_id": "1",
                "centre_id": "1",
                "booking_date": "2026-11-27",
                "booking_time": "09:00-17:00",
                "spaces_required": "1",
            },
        )

        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        mock_book.assert_called_once_with(
            {
                "request_id": 1,
                "centre_id": 1,
                "booking_date": "2026-11-27",
                "booking_time": "09:00-17:00",
                "spaces_required": 1,
            }
        )

    @patch("dashboard.views.api_client.update_booking", side_effect=ApiError("Not enough capacity available", 409))
    def test_update_booking_displays_api_conflict_error(self, mock_patch_booking):
        response = self.client.post(
            self.url,
            {
                "action": "update_booking",
                "booking_id": "10",
                "status": "Confirmed",
            },
            follow=True,
        )

        mock_patch_booking.assert_called_once_with(10, {"status": "Confirmed"})
        self.assertContains(response, "Not enough capacity available")