import copy
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from . import views
from .api_client import ApiError


class DashboardViewTests(TestCase):
    def setUp(self):
        self.original_requests = copy.deepcopy(views.MOCK_REQUESTS)
        self.url = reverse("dashboard_index")

    def tearDown(self):
        views.MOCK_REQUESTS[:] = self.original_requests

    @patch("dashboard.views.api_client.list_requests", side_effect=ApiError("API offline"))
    def test_renders_mock_data_and_counters_when_api_offline(self, _mock_list):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["api_connected"])
        self.assertEqual(response.context["outstanding_count"], 2)
        self.assertEqual(response.context["completed_count"], 1)
        self.assertContains(response, "Mock Data Mode")
        self.assertContains(response, "Bolton Community Centre")

    @patch("dashboard.views.api_client.list_centres")
    @patch("dashboard.views.api_client.list_requests")
    def test_renders_flask_api_data_when_connected(self, mock_requests, mock_centres):
        mock_requests.return_value = [
            {
                "request_id": 99,
                "description": "Live Flask request",
                "category": "Welfare",
                "priority": "high",
                "area": "Bolton",
                "status": "new",
                "created_at": "2026-11-26T12:00:00.000000",
            }
        ]
        mock_centres.return_value = [
            {
                "centre_id": 10,
                "name": "API Cooling Hub",
                "area": "Bolton",
                "capacity": 60,
                "opening_hours": "08:00 - 21:00",
                "status": "open",
            }
        ]

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["api_connected"])
        self.assertEqual(response.context["outstanding_count"], 1)
        self.assertEqual(response.context["completed_count"], 0)
        self.assertContains(response, "Flask API Connected")
        self.assertContains(response, "Live Flask request")
        self.assertContains(response, "API Cooling Hub")

    @patch("dashboard.views.api_client.list_requests", side_effect=ApiError("API offline"))
    def test_filters_by_query_category_priority_area_and_status(self, _mock_list):
        response = self.client.get(
            self.url,
            {
                "q": "cooling centre",
                "category": "Practical Assistance",
                "priority": "medium",
                "area": "Farnworth",
                "status": "in_progress",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["requests"]), 1)
        self.assertEqual(response.context["requests"][0]["request_id"], 2)

    @patch("dashboard.views.api_client.create_request", side_effect=ApiError("API offline"))
    def test_create_request_falls_back_to_mock_list(self, _mock_create):
        response = self.client.post(
            self.url,
            {
                "action": "create",
                "description": "Needs water bottles delivered",
                "category": "Practical Assistance",
                "priority": "high",
                "area": "Bolton",
            },
        )

        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.assertEqual(views.MOCK_REQUESTS[0]["description"], "Needs water bottles delivered")
        self.assertEqual(views.MOCK_REQUESTS[0]["category"], "Practical Assistance")
        self.assertEqual(views.MOCK_REQUESTS[0]["status"], "new")

    @patch("dashboard.views.api_client.update_request", side_effect=ApiError("API offline"))
    def test_update_status_falls_back_to_mock_list(self, _mock_update):
        response = self.client.post(
            self.url,
            {
                "action": "update_status",
                "request_id": "1",
                "status": "completed",
            },
        )

        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        updated = next(r for r in views.MOCK_REQUESTS if r["request_id"] == 1)
        self.assertEqual(updated["status"], "completed")

    @patch("dashboard.views.api_client.update_request")
    def test_update_status_sends_patch_to_flask_api(self, mock_update):
        response = self.client.post(
            self.url,
            {
                "action": "update_status",
                "request_id": "2",
                "status": "completed",
            },
        )

        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        mock_update.assert_called_once_with(2, {"status": "completed"})
