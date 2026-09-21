from rest_framework import serializers

from .models import FocusSession, FocusTelemetryPoint, StudySession, StudyTimer, Task, UserProjectLog, UserSkillProgress


class UserSkillProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSkillProgress
        fields = ["id", "skill", "is_done", "score", "notes", "completed_at"]


class StudySessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudySession
        fields = ["id", "label", "duration_minutes", "date", "created_at"]
        read_only_fields = ["id", "created_at"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class StudyTimerSerializer(serializers.ModelSerializer):
    remaining_seconds = serializers.SerializerMethodField()

    class Meta:
        model = StudyTimer
        fields = [
            "id",
            "label",
            "duration_minutes",
            "start_at",
            "end_at",
            "status",
            "remaining_seconds",
        ]

    def get_remaining_seconds(self, obj):
        return obj.remaining_seconds()


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ["id", "title", "description", "is_completed", "completed_at", "target_date", "mood", "category", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class ProjectSubmitSerializer(serializers.Serializer):
    project_id = serializers.IntegerField()
    github_url = serializers.URLField()
    live_url = serializers.URLField(required=False, allow_blank=True)
    reflection = serializers.CharField(required=False, allow_blank=True)

    def create(self, validated_data):
        return UserProjectLog.objects.create(**validated_data)


class FocusTelemetryPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = FocusTelemetryPoint
        fields = ["score", "state", "timestamp"]


class FocusSessionSerializer(serializers.ModelSerializer):
    telemetry = FocusTelemetryPointSerializer(many=True, read_only=True)

    class Meta:
        model = FocusSession
        fields = ["id", "session_id", "avg_focus_score", "total_distractions", "duration_seconds", "telemetry_points_count", "status", "status_key", "created_at", "telemetry"]


class DashboardSerializer(serializers.Serializer):
    total_skills_done = serializers.IntegerField()
    total_projects_done = serializers.IntegerField()
    current_level = serializers.CharField()
    current_field_slug = serializers.CharField()
    streak_days = serializers.IntegerField()
