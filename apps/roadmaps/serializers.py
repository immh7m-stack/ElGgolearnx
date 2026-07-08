from rest_framework import serializers

from .models import Field, Module, Playlist, Project, Skill, Track


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = [
            "id", "order_num", "title_ar", "title_en", "description_ar",
            "description_en", "duration_days", "skill_type", "resources",
        ]


class ModuleSerializer(serializers.ModelSerializer):
    skills = SkillSerializer(many=True, read_only=True)

    class Meta:
        model = Module
        fields = [
            "id", "order_num", "title_ar", "title_en", "summary_ar",
            "summary_en", "duration_days", "eng_query", "icon", "skills",
        ]


class PlaylistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Playlist
        fields = [
            "id", "lang", "youtube_url", "playlist_id", "channel_name",
            "title", "verified_year", "approx_views", "is_primary",
        ]


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = [
            "id", "order_num", "title_ar", "title_en", "description_ar",
            "description_en", "difficulty", "estimated_days", "skills_covered",
            "requirements", "bonus_features", "example_repo",
        ]


class TrackListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Track
        fields = [
            "id", "career_level", "goal_ar", "goal_en", "duration_months",
            "projects_needed", "can_do_ar", "can_do_en",
        ]


class TrackDetailSerializer(serializers.ModelSerializer):
    playlists = PlaylistSerializer(many=True, read_only=True)
    modules = ModuleSerializer(many=True, read_only=True)
    projects = ProjectSerializer(many=True, read_only=True)

    class Meta:
        model = Track
        fields = [
            "id", "career_level", "goal_ar", "goal_en", "duration_months",
            "projects_needed", "can_do_ar", "can_do_en", "ready_when_ar",
            "ready_when_en", "job_requirements", "playlists", "modules", "projects",
        ]


class FieldListSerializer(serializers.ModelSerializer):
    tracks = TrackListSerializer(many=True, read_only=True)

    class Meta:
        model = Field
        fields = [
            "id", "slug", "name_ar", "name_en", "icon", "color",
            "description_ar", "description_en", "tracks",
        ]


class FieldDetailSerializer(serializers.ModelSerializer):
    tracks = TrackListSerializer(many=True, read_only=True)

    class Meta:
        model = Field
        fields = [
            "id", "slug", "name_ar", "name_en", "icon", "color",
            "description_ar", "description_en", "tracks",
        ]
