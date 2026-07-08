from rest_framework import serializers

from .models import UserProjectLog, UserSkillProgress


class UserSkillProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSkillProgress
        fields = ["id", "skill", "is_done", "score", "notes", "completed_at"]


class ProjectSubmitSerializer(serializers.Serializer):
    project_id = serializers.IntegerField()
    github_url = serializers.URLField()
    live_url = serializers.URLField(required=False, allow_blank=True)
    reflection = serializers.CharField(required=False, allow_blank=True)

    def create(self, validated_data):
        return UserProjectLog.objects.create(**validated_data)


class DashboardSerializer(serializers.Serializer):
    total_skills_done = serializers.IntegerField()
    total_projects_done = serializers.IntegerField()
    current_level = serializers.CharField()
    current_field_slug = serializers.CharField()
    streak_days = serializers.IntegerField()
