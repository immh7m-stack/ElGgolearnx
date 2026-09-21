from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from apps.quizzes.models import VideoQuizCatalog, Question, QuizAttempt
from apps.quizzes.services.text_compressor import compress_transcript, clean_line_text
from apps.quizzes.services.ai_generator import fetch_or_generate_quizzes, normalize_questions_payload


class QuizzesTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.video_id = "test_video_123"
        self.catalog = VideoQuizCatalog.objects.create(
            video_id=self.video_id,
            title="Test Tech Video",
            is_generated=True
        )
        self.q_micro = Question.objects.create(
            catalog=self.catalog,
            question_type="MICRO",
            timestamp_start=300,
            timestamp_end=600,
            text="ما هو خيار الـ State Management المناسب؟",
            options=["Redux", "CSS", "HTML", "Bash"],
            correct_answer="Redux",
            explanation="Redux يدير حالة الواجهة مركزياً."
        )
        self.q_final = Question.objects.create(
            catalog=self.catalog,
            question_type="FINAL",
            timestamp_start=0,
            timestamp_end=0,
            text="كيف تعمل الـ Microservices Architecture؟",
            options=["خدمات مستقلة تواصل عبر APIs", "ملف واحد فقط", "صفحة ويب ثابتة", "تطبيق سطح مكتب"],
            correct_answer="خدمات مستقلة تواصل عبر APIs",
            explanation="الميكروسيرفس تقسم النظام لخدمات مستقلة."
        )

    def test_text_compressor(self):
        raw_text = "أهلاً وسهلاً بكم في القناة لا تنسى الاشتراك و Like and Subscribe"
        cleaned = clean_line_text(raw_text)
        self.assertNotIn("أهلاً وسهلاً", cleaned)
        self.assertNotIn("Subscribe", cleaned)

        transcript_items = [
            {"start": 0, "text": "مرحباً بكم اليوم سنتحدث عن Django Architecture"},
            {"start": 350, "text": "في هذه الجزئية نناقش Database Indexing في SQLite"}
        ]
        compressed = compress_transcript(transcript_items, chunk_duration_seconds=300)
        self.assertIn("CHUNK 0s - 300s", compressed)
        self.assertIn("CHUNK 300s - 600s", compressed)

    def test_caching_returns_stored_quizzes(self):
        # Should return cached=True and 0 network/AI latency
        res = fetch_or_generate_quizzes(self.video_id, trigger_mode="auto")
        self.assertTrue(res["cached"])
        self.assertEqual(res["video_id"], self.video_id)
        self.assertEqual(len(res["micro_questions"]), 1)
        self.assertEqual(len(res["final_questions"]), 1)

    def test_fetch_or_generate_api_endpoint(self):
        url = reverse("quizzes_api:fetch_or_generate")
        response = self.client.post(
            url,
            data={"video_id": self.video_id, "trigger_mode": "auto"},
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertEqual(json_data["status"], "success")
        self.assertTrue(json_data["cached"])

    def test_fetch_or_generate_regenerates_when_catalog_has_no_questions(self):
        self.catalog.is_generated = True
        self.catalog.save(update_fields=["is_generated"])
        self.catalog.questions.all().delete()

        result = fetch_or_generate_quizzes(self.video_id, trigger_mode="on_demand")

        self.assertEqual(result["status"], "success")
        self.assertTrue(result["micro_questions"] or result["final_questions"])
        self.assertGreaterEqual(self.catalog.questions.count(), 1)

    def test_submit_quiz_api_endpoint(self):
        url = reverse("quizzes_api:submit")
        payload = {
            "video_id": self.video_id,
            "answers": {
                str(self.q_micro.id): "Redux",
                str(self.q_final.id): "ملف واحد فقط"  # Wrong answer
            }
        }
        response = self.client.post(
            url,
            data=payload,
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertEqual(json_data["status"], "success")
        self.assertEqual(json_data["score"], 50.0)  # 1 out of 2 correct = 50%
        self.assertEqual(QuizAttempt.objects.count(), 1)
        attempt = QuizAttempt.objects.first()
        self.assertEqual(attempt.score, 50.0)

    def test_watch_page_exposes_quiz_panel(self):
        url = reverse("library:watch")
        response = self.client.get(
            url,
            {"url": "https://www.youtube.com/watch?v=dummy-video", "title": "Demo Video"},
        )
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertIn("اختبارات الفيديو المباشرة", html)
        self.assertIn("تحميل الاختبارات", html)
        self.assertIn("نظرة سريعة", html)
        self.assertIn("قائمة الدروس", html)

    def test_exam_page_renders_combined_and_separate_sections(self):
        url = reverse("quizzes:exam_detail", kwargs={"video_id": self.video_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertIn("الاختبار المجمع", html)
        self.assertIn("الأسئلة المنفصلة", html)

    def test_progress_dashboard_shows_recent_quiz_attempts(self):
        user = get_user_model().objects.create_user(username="quizuser", email="quiz@example.com", password="secret123")
        self.client.force_login(user)
        QuizAttempt.objects.create(user=user, video_catalog=self.catalog, score=85.0, user_answers={})

        response = self.client.get(reverse("progress:dashboard"))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertIn("نتائج الاختبارات السابقة", html)
        self.assertIn("85%", html)
        self.assertIn("أفضل درجة", html)
        self.assertIn("المتوسط", html)
        self.assertIn("مؤشرات سريعة", html)
        self.assertIn("ملخص أسبوعي", html)

    def test_normalize_questions_payload_fills_missing_options_and_filters_invalid_items(self):
        raw_payload = {
            "micro_questions": [
                {
                    "text": "ما أثر استخدام Cache في الأداء؟",
                    "options": ["يقلل الاستجابة", "يُسرع الوصول", "يُعطل التطبيق", "يقلل الذاكرة"],
                    "correct_answer": "يُسرع الوصول",
                    "explanation": "يوفر Cache نتائج سريعة."
                },
                {
                    "text": "",
                    "options": ["A", "B"],
                    "correct_answer": "A",
                    "explanation": ""
                }
            ],
            "final_questions": [
                {
                    "text": "كيف توازن بين الأداء والتعقيد؟",
                    "options": ["باختيار الحلول المناسبة", "بإيقاف التخزين", "بإزالة التوثيق", "بإنهاء المشروع"],
                    "correct_answer": "باختيار الحلول المناسبة",
                    "explanation": "التوازن يحقق التقدم بدون تعقيد غير ضروري."
                }
            ]
        }

        normalized = normalize_questions_payload(raw_payload)
        self.assertEqual(len(normalized["micro_questions"]), 1)
        self.assertEqual(len(normalized["final_questions"]), 1)
        self.assertEqual(len(normalized["micro_questions"][0]["options"]), 4)
        self.assertIn("سؤال", normalized["micro_questions"][0]["text"])
