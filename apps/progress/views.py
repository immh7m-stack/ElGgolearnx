from datetime import date

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.accounts.models import LearnerStats
from apps.roadmaps.models import Field, Project, Skill, Track

from .models import UserProjectLog, UserSkillProgress


@login_required
def dashboard(request):
    stats, _ = LearnerStats.objects.get_or_create(user=request.user)
    skill_progress = UserSkillProgress.objects.filter(user=request.user, is_done=True).select_related(
        "skill__module__track__field"
    )
    project_logs = UserProjectLog.objects.filter(user=request.user).select_related("project__track__field")

    current_field = None
    current_track = None
    progress_pct = 0
    track_projects_total = 0
    track_projects_done = 0
    project_progress_pct = 0
    if stats.current_field_slug:
        current_field = Field.objects.filter(slug=stats.current_field_slug).first()
        if current_field and stats.current_level:
            current_track = Track.objects.filter(field=current_field, career_level=stats.current_level).first()
            if current_track:
                total = Skill.objects.filter(module__track=current_track).count()
                done = skill_progress.filter(skill__module__track=current_track).count()
                progress_pct = int((done / total) * 100) if total else 0
                track_projects_total = Project.objects.filter(track=current_track).count()
                track_projects_done = UserProjectLog.objects.filter(
                    user=request.user, project__track=current_track
                ).count()
                project_progress_pct = (
                    int((track_projects_done / track_projects_total) * 100) if track_projects_total else 0
                )

    lang = "ar"
    if hasattr(request.user, "profile"):
        lang = request.user.profile.preferred_lang

    return render(
        request,
        "progress/dashboard.html",
        {
            "stats": stats,
            "skill_progress": skill_progress[:20],
            "project_logs": project_logs,
            "current_field": current_field,
            "current_track": current_track,
            "progress_pct": progress_pct,
            "track_projects_total": track_projects_total,
            "track_projects_done": track_projects_done,
            "project_progress_pct": project_progress_pct,
            "lang": lang,
        },
    )


def _update_learner_stats(user):
    stats, _ = LearnerStats.objects.get_or_create(user=user)
    stats.total_skills_done = UserSkillProgress.objects.filter(user=user, is_done=True).count()
    stats.total_projects_done = UserProjectLog.objects.filter(user=user).count()
    stats.last_active = date.today()
    stats.save()


@login_required
def toggle_skill(request, skill_id):
    if request.method != "POST":
        from django.http import HttpResponseNotAllowed
        return HttpResponseNotAllowed(["POST"])
    skill = get_object_or_404(Skill, pk=skill_id)
    progress, created = UserSkillProgress.objects.get_or_create(user=request.user, skill=skill)
    progress.is_done = not progress.is_done
    progress.completed_at = timezone.now() if progress.is_done else None
    progress.save()
    _update_learner_stats(request.user)
    stats, _ = LearnerStats.objects.get_or_create(user=request.user)
    stats.current_field_slug = skill.module.track.field.slug
    stats.current_level = skill.module.track.career_level
    stats.save()
    track = skill.module.track
    return redirect("roadmaps:track", slug=track.field.slug, level=track.career_level)


@login_required
def submit_project(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    if request.method == "POST":
        github_url = request.POST.get("github_url", "").strip()
        reflection = request.POST.get("reflection", "").strip()
        live_url = request.POST.get("live_url", "").strip()
        if github_url:
            UserProjectLog.objects.update_or_create(
                user=request.user,
                project=project,
                defaults={"github_url": github_url, "reflection": reflection, "live_url": live_url},
            )
            _update_learner_stats(request.user)
    track = project.track
    return redirect("roadmaps:track", slug=track.field.slug, level=track.career_level)
