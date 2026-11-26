import copy
from unittest.mock import patch
from urllib.error import URLError

from django.test import TestCase
from django.urls import reverse

from . import views


class DashboardViewTests(TestCase):
    def setUp(self):
        self.original_requests = copy.deepcopy(views.MOCK_REQUESTS)
        self.url = reverse("dashboard_index")

    def tearDown(self):
        views.MOCK_REQUESTS[:] = self.original_requests

    @patch("dashboard.views._fetch_json", side_effect=URLError("API offline"))
    def test_renders_mock_data_and_counters_when_api_offline(self, _mock_fetch):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["api_connected"])
        self.assertEqual(response.context["outstanding_count"], 2)
        self.assertEqual(response.context["completed_count"], 1)
        self.assertContains(response, "Mock Data Mode")
        self.assertContains(response, "Bolton Community Centre")

    @patch("dashboard.views._fetch_json")
    def test_renders_flask_api_data_when_connected(self, mock_fetch):
        mock_fetch.side_effect = [
            [
                {
                    "request_id": 99,
                    "description": "Live Flask request",
                    "category": "Welfare",
                    "priority": "High",
                    "area": "Bolton",
                    "status": "New",
                    "created_at": "2026-11-26 12:00",
                }
            ],
            [
                {
                    "centre_id": 10,
                    "name": "API Cooling Hub",
                    "area": "Bolton",
                    "capacity": 60,
                    "opening_hours": "08:00 - 21:00",
                    "status": "Open",
                }
            ],
        ]

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["api_connected"])
        self.assertEqual(response.context["outstanding_count"], 1)
        self.assertEqual(response.context["completed_count"], 0)
        self.assertContains(response, "Flask API Connected")
        self.assertContains(response, "Live Flask request")
        self.assertContains(response, "API Cooling Hub")

    @patch("dashboard.views._fetch_json", side_effect=URLError("API offline"))
    def test_filters_by_query_category_priority_area_and_status(self, _mock_fetch):
        response = self.client.get(
            self.url,
            {
                "q": "cooling centre",
                "category": "Practical Assistance",
                "priority": "Medium",
                "area": "Farnworth",
                "status": "In Progress",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["requests"]), 1)
        self.assertEqual(response.context["requests"][0]["request_id"], 2)

    @patch("dashboard.views._send_json", side_effect=URLError("API offline"))
    def test_create_request_falls_back_to_mock_list(self, _mock_send):
        response = self.client.post(
            self.url,
            {
                "action": "create",
                "description": "Needs water bottles delivered",
                "category": "Practical Assistance",
                "priority": "High",
                "area": "Bolton",
            },
        )

        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.assertEqual(views.MOCK_REQUESTS[0]["description"], "Needs water bottles delivered")
        self.assertEqual(views.MOCK_REQUESTS[0]["category"], "Practical Assistance")
        self.assertEqual(views.MOCK_REQUESTS[0]["status"], "New")

    @patch("dashboard.views._send_json", side_effect=URLError("API offline"))
    def test_update_status_falls_back_to_mock_list(self, _mock_send):
        response = self.client.post(
            self.url,
            {
                "action": "update_status",
                "request_id": "1",
                "status": "Completed",
            },
        )

        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        updated = next(r for r in views.MOCK_REQUESTS if r["request_id"] == 1)
        self.assertEqual(updated["status"], "Completed")

    @patch("dashboard.views._send_json")
    def test_update_status_sends_patch_to_flask_api(self, mock_send):
        response = self.client.post(
            self.url,
            {
                "action": "update_status",
                "request_id": "2",
                "status": "Completed",
            },
        )

        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        mock_send.assert_called_once_with("/requests/2", {"status": "Completed"}, method="PATCH")
