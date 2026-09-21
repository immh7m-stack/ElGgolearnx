from rest_framework import serializers
from apps.quizzes.models import VideoQuizCatalog, Question, QuizAttempt


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = [
            "id",
            "question_type",
            "timestamp_start",
            "timestamp_end",
            "text",
            "options",
            "correct_answer",
            "explanation",
        ]


class VideoQuizCatalogSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = VideoQuizCatalog
        fields = ["id", "video_id", "title", "is_generated", "created_at", "questions"]


class FetchOrGenerateRequestSerializer(serializers.Serializer):
    video_id = serializers.CharField(max_length=50, required=True)
    trigger_mode = serializers.ChoiceField(
        choices=["auto", "on_demand"], default="auto", required=False
    )


class QuizSubmissionRequestSerializer(serializers.Serializer):
    video_id = serializers.CharField(max_length=50, required=True)
    answers = serializers.DictField(
        child=serializers.CharField(allow_blank=True),
        required=True,
        help_text="Dict mapping question_id to selected answer string"
    )


class QuizAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizAttempt
        fields = ["id", "user", "video_catalog", "score", "user_answers", "completed_at"]
