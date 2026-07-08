from django.db.models import Count
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import LearnerStats
from apps.roadmaps.models import Field, Skill, Track

from .models import UserProjectLog, UserSkillProgress
from .serializers import DashboardSerializer, ProjectSubmitSerializer, UserSkillProgressSerializer


class ToggleSkillAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, skill_id):
        skill = Skill.objects.get(pk=skill_id)
        progress, _ = UserSkillProgress.objects.get_or_create(user=request.user, skill=skill)
        progress.is_done = not progress.is_done
        progress.completed_at = timezone.now() if progress.is_done else None
        progress.save()
        stats, _ = LearnerStats.objects.get_or_create(user=request.user)
        stats.total_skills_done = UserSkillProgress.objects.filter(user=request.user, is_done=True).count()
        stats.save()
        return Response(UserSkillProgressSerializer(progress).data)


class SubmitProjectAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ProjectSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        from apps.roadmaps.models import Project

        project = Project.objects.get(pk=data["project_id"])
        log = UserProjectLog.objects.create(
            user=request.user,
            project=project,
            github_url=data["github_url"],
            live_url=data.get("live_url", ""),
            reflection=data.get("reflection", ""),
        )
        stats, _ = LearnerStats.objects.get_or_create(user=request.user)
        stats.total_projects_done = UserProjectLog.objects.filter(user=request.user).count()
        stats.save()
        return Response({"id": log.id, "status": log.status}, status=status.HTTP_201_CREATED)


class DashboardAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        stats, _ = LearnerStats.objects.get_or_create(user=request.user)
        skills_done = UserSkillProgress.objects.filter(user=request.user, is_done=True).count()
        projects_done = UserProjectLog.objects.filter(user=request.user).count()
        data = {
            "total_skills_done": skills_done,
            "total_projects_done": projects_done,
            "current_level": stats.current_level,
            "current_field_slug": stats.current_field_slug,
            "streak_days": stats.streak_days,
            "last_active": stats.last_active,
        }
        return Response(data)


class FieldStatsAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, field_slug):
        field = Field.objects.get(slug=field_slug)
        tracks = Track.objects.filter(field=field)
        result = []
        for track in tracks:
            total = Skill.objects.filter(module__track=track).count()
            done = UserSkillProgress.objects.filter(
                user=request.user, is_done=True, skill__module__track=track
            ).count()
            result.append({
                "level": track.career_level,
                "total_skills": total,
                "done_skills": done,
                "percent": int((done / total) * 100) if total else 0,
            })
        return Response({"field": field_slug, "tracks": result})
