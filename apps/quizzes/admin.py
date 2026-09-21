from django.contrib import admin
from apps.quizzes.models import VideoQuizCatalog, Question, QuizAttempt


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    fields = ("question_type", "timestamp_start", "timestamp_end", "text", "correct_answer")


@admin.register(VideoQuizCatalog)
class VideoQuizCatalogAdmin(admin.ModelAdmin):
    list_display = ("video_id", "title", "is_generated", "created_at")
    list_filter = ("is_generated", "created_at")
    search_fields = ("video_id", "title")
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "catalog", "question_type", "timestamp_start", "text_snippet")
    list_filter = ("question_type", "catalog")
    search_fields = ("text", "explanation", "catalog__video_id")

    def text_snippet(self, obj):
        return obj.text[:50]
    text_snippet.short_description = "Question Text"


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "video_catalog", "score", "completed_at")
    list_filter = ("completed_at", "video_catalog")
    search_fields = ("user__email", "video_catalog__video_id")
