from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import FocusSession, StudySession


class StudySessionAPITests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="tester", email="tester@example.com", password="secret123")

    def test_authenticated_user_can_create_study_session(self):
        url = reverse("api-study-session")
        payload = {
            "label": "Django basics",
            "duration_minutes": 120,
            "date": "2026-07-08",
        }

        self.client.force_authenticate(self.user)
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(StudySession.objects.count(), 1)
        session = StudySession.objects.get()
        self.assertEqual(session.user, self.user)
        self.assertEqual(session.duration_minutes, 120)
        self.assertEqual(session.label, "Django basics")


class StudyTimerAPITests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="timer_tester", email="timer@example.com", password="secret123")
        self.client.force_authenticate(self.user)

    def test_authenticated_user_can_start_and_restore_timer(self):
        url = reverse("api-study-timer")
        response = self.client.post(url, {"label": "جلسة تجربة", "duration_minutes": 5}, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertIn("remaining_seconds", response.data)
        self.assertEqual(response.data["label"], "جلسة تجربة")

        restore = self.client.get(url)
        self.assertEqual(restore.status_code, 200)
        self.assertTrue(restore.data["active"])
        self.assertEqual(restore.data["label"], "جلسة تجربة")

    def test_authenticated_user_can_finish_timer(self):
        start_url = reverse("api-study-timer")
        self.client.post(start_url, {"label": "اختبار الانتهاء", "duration_minutes": 1}, format="json")

        finish_url = reverse("api-study-timer-finish")
        response = self.client.post(finish_url, {}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertIn("finished_session", response.data)
        self.assertEqual(response.data["finished_session"]["label"], "اختبار الانتهاء")


class FocusAnalysisAPITests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="focus_engine", email="focus_engine@example.com", password="secret123")
        self.client.force_authenticate(self.user)

    @patch("apps.progress.api_views.analyze_focus_frame")
    def test_focus_analysis_api_returns_engine_result(self, mock_analyze):
        mock_analyze.return_value = {
            "score": 92.0,
            "state": "Focused",
            "note": "انتباه ممتاز",
            "is_focused": True,
            "is_drowsy": False,
            "iris_distracted": False,
            "gaze_direction": "Facing Screen",
            "engine": "detector",
        }

        response = self.client.post(reverse("api-focus-analysis"), {"image_base64": "data:image/jpeg;base64,abc"}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["score"], 92.0)
        self.assertEqual(response.data["note"], "انتباه ممتاز")
        self.assertEqual(response.data["engine"], "detector")


class FocusSessionAPITests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="focus_tester", email="focus@example.com", password="secret123")
        self.client.force_authenticate(self.user)

    def test_focus_session_payload_is_stored_and_exposed_on_dashboard(self):
        payload = {
            "session_summary": {
                "session_id": 77,
                "avg_focus_score": 84.5,
                "total_distractions": 2,
                "duration_seconds": 300,
                "telemetry_points_count": 2,
            },
            "telemetry": [
                {"score": 88.0, "state": "Focused", "timestamp": "2026-07-27 15:00:00.000"},
                {"score": 45.0, "state": "Distracted - Looking Left", "timestamp": "2026-07-27 15:00:05.000"},
            ],
        }

        response = self.client.post(reverse("api-focus-sessions"), payload, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(FocusSession.objects.count(), 1)
        self.assertEqual(FocusSession.objects.get().telemetry_points.count(), 2)

        self.client.force_login(self.user)
        dashboard_response = self.client.get(reverse("progress:dashboard"))
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertIn("focus_summary", dashboard_response.context)
        self.assertEqual(dashboard_response.context["focus_summary"]["status_key"], "good")
