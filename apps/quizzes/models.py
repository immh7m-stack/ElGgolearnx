from django.db import models
from django.conf import settings


class VideoQuizCatalog(models.Model):
    """
    جدول لتتبع الفيديوهات المخزنة لمنع التوليد المكرر.
    """
    video_id = models.CharField(max_length=50, unique=True, db_index=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    is_generated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Video Quiz Catalog"
        verbose_name_plural = "Video Quiz Catalogs"

    def __str__(self):
        return f"{self.video_id} - Generated: {self.is_generated}"


class Question(models.Model):
    QUESTION_TYPES = (
        ("MICRO", "Micro Question (5-10 min mark)"),
        ("FINAL", "Comprehensive Question (Self-Test)"),
    )

    catalog = models.ForeignKey(VideoQuizCatalog, related_name="questions", on_delete=models.CASCADE)
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPES)

    # التوقيت الزمني لظهور السؤال اللحظي
    timestamp_start = models.PositiveIntegerField(default=0, help_text="بداية الجزئية بالثواني")
    timestamp_end = models.PositiveIntegerField(default=0, help_text="نهاية الجزئية بالثواني")

    # تفاصيل السؤال
    text = models.TextField(help_text="نص السؤال بالعربي مع المصطلحات التقنية بالإنجليزي")
    options = models.JSONField(help_text="قائمة الاختيارات ['A', 'B', 'C', 'D']")
    correct_answer = models.CharField(max_length=255)
    explanation = models.TextField(help_text="الشرح لتعزيز التعلم النشط")

    class Meta:
        ordering = ["timestamp_start", "id"]
        verbose_name = "Question"
        verbose_name_plural = "Questions"

    def __str__(self):
        return f"[{self.question_type}] {self.text[:40]}"


class QuizAttempt(models.Model):
    """
    تتبع محاولات وتقييم المستخدم
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    video_catalog = models.ForeignKey(VideoQuizCatalog, on_delete=models.CASCADE, related_name="attempts")
    score = models.FloatField(default=0.0)
    user_answers = models.JSONField(default=dict)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-completed_at"]
        verbose_name = "Quiz Attempt"
        verbose_name_plural = "Quiz Attempts"

    def __str__(self):
        user_str = self.user.email if self.user else "Anonymous"
        return f"Attempt by {user_str} on {self.video_catalog.video_id} ({self.score}%)"
