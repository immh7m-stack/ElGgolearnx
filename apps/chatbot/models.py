from django.conf import settings
from django.db import models


class ChatSession(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_sessions", null=True, blank=True
    )
    field_slug = models.CharField(max_length=100, blank=True)
    track_level = models.CharField(max_length=20, blank=True)
    module_title = models.CharField(max_length=300, blank=True)
    page_path = models.CharField(
        max_length=512,
        blank=True,
        default="",
        help_text="مسار الصفحة عند بدء الشات (يفيد الأسئلة عن التنقل في المنصة).",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Session {self.pk} — {self.field_slug}"


class ChatMessage(models.Model):
    ROLE_CHOICES = [
        ("user", "User"),
        ("assistant", "Assistant"),
    ]
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"
