from datetime import date

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.accounts.models import LearnerStats
from apps.quizzes.models import QuizAttempt
from apps.roadmaps.models import Field, Project, Skill, Track

from .models import FocusSession, StudySession, UserProjectLog, UserSkillProgress


@login_required
def dashboard(request):
    stats, _ = LearnerStats.objects.get_or_create(user=request.user)
    skill_progress = UserSkillProgress.objects.filter(user=request.user, is_done=True).select_related(
        "skill__module__track__field"
    )
    project_logs = UserProjectLog.objects.filter(user=request.user).select_related("project__track__field")
    quiz_attempts = QuizAttempt.objects.filter(user=request.user).select_related("video_catalog").order_by("-completed_at")[:6]
    quiz_scores = [attempt.score for attempt in quiz_attempts if attempt.score is not None]
    best_quiz_score = round(max(quiz_scores), 1) if quiz_scores else 0
    average_quiz_score = round(sum(quiz_scores) / len(quiz_scores), 1) if quiz_scores else 0
    latest_quiz_score = round(quiz_attempts[0].score, 1) if quiz_attempts else 0
    study_sessions_all = StudySession.objects.filter(user=request.user)
    study_sessions = study_sessions_all.order_by("-created_at")[:10]
    study_totals = study_sessions_all.aggregate(total_minutes=Sum("duration_minutes"))
    total_study_minutes = study_totals["total_minutes"] or 0
    today = timezone.localdate()
    today_study_minutes = study_sessions_all.filter(date=today).aggregate(total_minutes=Sum("duration_minutes"))["total_minutes"] or 0
    daily_breakdown = list(
        study_sessions_all.values("date").annotate(total_minutes=Sum("duration_minutes")).order_by("-date")[:7]
    )
    focus_sessions = FocusSession.objects.filter(user=request.user).order_by("-created_at")[:5]
    latest_focus = focus_sessions.first()
    focus_summary = None
    if latest_focus:
        focus_summary = {
            "status": latest_focus.status,
            "status_key": latest_focus.status_key,
            "avg_focus_score": latest_focus.avg_focus_score,
            "total_distractions": latest_focus.total_distractions,
            "duration_seconds": latest_focus.duration_seconds,
            "telemetry_points_count": latest_focus.telemetry_points_count,
            "created_at": latest_focus.created_at,
        }

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
            "quiz_attempts": quiz_attempts,
            "best_quiz_score": best_quiz_score,
            "average_quiz_score": average_quiz_score,
            "latest_quiz_score": latest_quiz_score,
            "current_field": current_field,
            "current_track": current_track,
            "progress_pct": progress_pct,
            "track_projects_total": track_projects_total,
            "track_projects_done": track_projects_done,
            "project_progress_pct": project_progress_pct,
            "lang": lang,
            "study_sessions": study_sessions,
            "focus_sessions": focus_sessions,
            "focus_summary": focus_summary,
            "total_study_minutes": total_study_minutes,
            "total_study_hours": round(total_study_minutes / 60, 1),
            "today_study_minutes": today_study_minutes,
            "today_study_hours": round(today_study_minutes / 60, 1),
            "daily_breakdown": [
                {
                    "date": item["date"],
                    "total_minutes": item["total_minutes"],
                    "total_hours": round(item["total_minutes"] / 60, 1),
                }
                for item in daily_breakdown
            ],
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
