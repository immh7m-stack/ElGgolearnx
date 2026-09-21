from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from .views import search_page


class SearchPageTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_search_page_does_not_render_book_search_section(self):
        request = self.factory.get("/library/search/", {"q": "python"})

        with patch("apps.library.views.youtube.search_playlists", return_value=[]):
            response = search_page(request)

        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertNotIn("Free books & PDFs", html)
        self.assertNotIn('option value="books"', html)
        self.assertNotIn('name="search_type"', html)


class ReadBookPageTests(TestCase):
    def test_read_book_page_handles_literal_none_book_id(self):
        user = get_user_model().objects.create_user(username="reader", email="reader@example.com", password="secret123")
        self.client.force_login(user)

        response = self.client.get(
            "/library/read-book/",
            {"book_id": "None", "title": "Cyber Way", "is_pdf": "1"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Invalid")


class WatchPageTests(TestCase):
    def test_watch_page_loads_quiz_scripts_for_direct_video_without_playlist_videos(self):
        with patch("apps.library.views.youtube.get_playlist_videos", return_value=[]), patch(
            "apps.library.views.youtube.extract_video_id_from_url", return_value="direct_video_123"
        ), patch("apps.library.views.record_playlist_open"):
            response = self.client.get(
                "/library/watch/",
                {"url": "https://www.youtube.com/watch?v=direct_video_123"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "watch_embed_player.js")
        self.assertContains(response, "quizzes_watch.js")
