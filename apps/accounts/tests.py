from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from apps.quizzes.models import VideoQuizCatalog, Question, QuizAttempt


class ProfilePageTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username="profileuser",
            email="profile@example.com",
            password="secret123",
        )
        self.catalog = VideoQuizCatalog.objects.create(
            video_id="profile_video_1",
            title="Profile Video",
            is_generated=True,
        )
        self.question1 = Question.objects.create(
            catalog=self.catalog,
            question_type="FINAL",
            timestamp_start=0,
            timestamp_end=0,
            text="ما هو أفضل نهج للتعامل مع أخطاء الشبكة؟",
            options=["Retry", "Ignore", "Log only", "Shutdown"],
            correct_answer="Retry",
            explanation="إعادة المحاولة هي طريقة سليمة للتعامل مع أخطاء الشبكة المؤقتة.",
        )
        self.question2 = Question.objects.create(
            catalog=self.catalog,
            question_type="FINAL",
            timestamp_start=0,
            timestamp_end=0,
            text="ما الفائدة من كتابة Unit Tests؟",
            options=["تحسين الثقة", "زيادة التعقيد", "تأخير الإطلاق", "إخفاء الأخطاء"],
            correct_answer="تحسين الثقة",
            explanation="Unit Tests تجعل التغيير أكثر أمانًا وتكشف الأخطاء مبكرًا.",
        )
        self.attempt = QuizAttempt.objects.create(
            user=self.user,
            video_catalog=self.catalog,
            score=75.0,
            user_answers={
                str(self.question1.id): "Retry",
                str(self.question2.id): "تأخير الإطلاق",
            },
        )

    def test_profile_page_shows_quiz_summary_and_details(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")

        self.assertIn("متوسط الدرجة", html)
        self.assertIn("75,0%", html)
        self.assertIn("عدد المحاولات الناجحة", html)
        self.assertIn("1 محاولة", html)
        self.assertIn("Profile Video", html)
        self.assertIn("ما هو أفضل نهج للتعامل مع أخطاء الشبكة؟", html)
        self.assertIn("إجابتك:", html)
        self.assertIn("Retry", html)
        self.assertIn("الإجابة الصحيحة:", html)
        self.assertIn("1/2 صحيح", html)
