import base64
import io
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

try:
    import cv2
except ImportError:  # pragma: no cover - runtime environment may not have OpenCV
    cv2 = None

try:
    import numpy as np
except ImportError:  # pragma: no cover - runtime environment may not have NumPy
    np = None

from django.conf import settings
from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import LearnerStats
from apps.roadmaps.models import Field, Skill, Track

from .models import FocusSession, FocusTelemetryPoint, StudySession, StudyTimer, Task, UserProjectLog, UserSkillProgress
from .serializers import (
    DashboardSerializer,
    FocusSessionSerializer,
    ProjectSubmitSerializer,
    StudySessionSerializer,
    StudyTimerSerializer,
    TaskSerializer,
    UserSkillProgressSerializer,
)
_detector_cache: Optional[Any] = None


def _get_focus_detector() -> Optional[Any]:
    global _detector_cache
    if _detector_cache is not None:
        return _detector_cache
    try:
        from apps.monitoring.engine.detector import FaceFocusDetector
    except Exception as exc:  # pragma: no cover - defensive fallback
        return None

    try:
        _detector_cache = FaceFocusDetector(max_num_faces=1)
    except Exception as exc:  # pragma: no cover - defensive fallback
        _detector_cache = None
    return _detector_cache


def analyze_focus_frame(image_data: Optional[str]) -> Dict[str, Any]:
    if not image_data:
        return {
            "score": 0.0,
            "state": "No frame",
            "note": "لا توجد صورة لتحليلها",
            "is_focused": False,
            "is_drowsy": False,
            "iris_distracted": False,
            "gaze_direction": "",
            "engine": "fallback",
        }

    try:
        if cv2 is None or np is None:
            raise RuntimeError("OpenCV/NumPy unavailable")

        if image_data.startswith("data:"):
            header, encoded = image_data.split(",", 1)
            if ";base64" not in header:
                raise ValueError("Unsupported image format")
            image_bytes = base64.b64decode(encoded)
        else:
            image_bytes = base64.b64decode(image_data)

        array = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(array, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Could not decode image")

        detector = _get_focus_detector()
        if detector is None:
            raise RuntimeError("Face detector unavailable")

        _, pose = detector.process_frame(image)
        if pose is None:
            return {
                "score": 0.0,
                "state": "No face",
                "note": "لم يتم اكتشاف وجه",
                "is_focused": False,
                "is_drowsy": False,
                "iris_distracted": False,
                "gaze_direction": "",
                "engine": "detector",
            }

        if pose.is_drowsy:
            state = "Drowsiness Detected"
            note = "تشتت واضح"
        elif pose.iris_distracted:
            state = f"Distracted - {pose.iris_direction}"
            note = "تشتت واضح"
        elif not pose.is_focused:
            state = f"Distracted - {pose.gaze_direction}"
            note = "تشتت خفيف"
        else:
            state = "Focused"
            note = "انتباه ممتاز"

        score = max(0.0, min(100.0, float(pose.focus_score or 0.0)))
        return {
            "score": round(score, 1),
            "state": state,
            "note": note,
            "is_focused": bool(pose.is_focused),
            "is_drowsy": bool(pose.is_drowsy),
            "iris_distracted": bool(pose.iris_distracted),
            "gaze_direction": pose.gaze_direction or "",
            "engine": "detector",
        }
    except Exception:
        return {
            "score": 0.0,
            "state": "Analysis fallback",
            "note": "تم استخدام وضع بديل بسبب عدم توفر المحلل",
            "is_focused": False,
            "is_drowsy": False,
            "iris_distracted": False,
            "gaze_direction": "",
            "engine": "fallback",
        }


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


class StudySessionAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = StudySessionSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        session = serializer.save()
        return Response(StudySessionSerializer(session).data, status=status.HTTP_201_CREATED)


class StudyTimerAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        timer = StudyTimer.objects.filter(user=request.user, status="active").order_by("-created_at").first()
        if not timer:
            return Response({"active": False})
        if timer.end_at <= timezone.now():
            timer.finalize()
            return Response(
                {
                    "active": False,
                    "finished_session": {
                        "label": timer.label,
                        "duration_minutes": timer.duration_minutes,
                    },
                }
            )
        return Response(
            {
                "active": True,
                "id": timer.id,
                "label": timer.label,
                "duration_minutes": timer.duration_minutes,
                "remaining_seconds": timer.remaining_seconds(),
                "ends_at": timer.end_at.isoformat(),
            }
        )

    def post(self, request):
        label = request.data.get("label", "")
        duration = request.data.get("duration_minutes", 25)
        try:
            duration = int(duration)
        except (TypeError, ValueError):
            duration = 25
        duration = max(1, min(duration, 480))
        StudyTimer.objects.filter(user=request.user, status="active").update(status="cancelled")
        start_at = timezone.now()
        end_at = start_at + timedelta(minutes=duration)
        timer = StudyTimer.objects.create(
            user=request.user,
            label=label.strip(),
            duration_minutes=duration,
            start_at=start_at,
            end_at=end_at,
        )
        return Response(StudyTimerSerializer(timer).data, status=status.HTTP_201_CREATED)


class StudyTimerFinishAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        timer = StudyTimer.objects.filter(user=request.user, status="active").order_by("-created_at").first()
        if not timer:
            return Response({"detail": "No active timer."}, status=status.HTTP_404_NOT_FOUND)
        timer.finalize()
        return Response(
            {
                "finished_session": {
                    "label": timer.label,
                    "duration_minutes": timer.duration_minutes,
                }
            }
        )


class StudyTimerCancelAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        timer = StudyTimer.objects.filter(user=request.user, status="active").order_by("-created_at").first()
        if not timer:
            return Response({"detail": "No active timer."}, status=status.HTTP_404_NOT_FOUND)
        timer.cancel()
        return Response({"cancelled": True})


class FocusAnalysisAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        image_base64 = request.data.get("image_base64") or request.data.get("image")
        if not image_base64:
            return Response({"detail": "image_base64 is required"}, status=status.HTTP_400_BAD_REQUEST)
        result = analyze_focus_frame(image_base64)
        return Response(result, status=status.HTTP_200_OK)


class FocusSessionAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        session_summary = request.data.get("session_summary", {})
        telemetry = request.data.get("telemetry", [])
        if not session_summary:
            return Response({"detail": "session_summary is required"}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        if not user.is_authenticated:
            provided_user_id = request.data.get("user_id")
            secret = request.headers.get("X-Elgolearn-Secret") or request.data.get("secret")
            expected_secret = getattr(settings, "ELGOLEARN_SYNC_SECRET", "")
            if not provided_user_id or not secret or secret != expected_secret:
                return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
            from django.contrib.auth import get_user_model
            UserModel = get_user_model()
            try:
                user = UserModel.objects.get(pk=provided_user_id)
            except UserModel.DoesNotExist:
                return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        status_key = "good"
        avg_score = float(session_summary.get("avg_focus_score", 0) or 0)
        if avg_score >= 85:
            status_key = "excellent"
        elif avg_score >= 70:
            status_key = "good"
        elif avg_score >= 50:
            status_key = "warning"
        else:
            status_key = "critical"

        focus_session = FocusSession.objects.create(
            user=user,
            session_id=int(session_summary.get("session_id") or 0),
            avg_focus_score=avg_score,
            total_distractions=int(session_summary.get("total_distractions") or 0),
            duration_seconds=int(session_summary.get("duration_seconds") or 0),
            telemetry_points_count=int(session_summary.get("telemetry_points_count") or len(telemetry)),
            status=status_key,
            status_key=status_key,
        )
        for item in telemetry:
            timestamp_value = item.get("timestamp")
            if not timestamp_value:
                continue
            parsed_timestamp = datetime.strptime(timestamp_value, "%Y-%m-%d %H:%M:%S.%f")
            if timezone.is_naive(parsed_timestamp):
                parsed_timestamp = timezone.make_aware(parsed_timestamp, timezone.get_current_timezone())
            FocusTelemetryPoint.objects.create(
                session=focus_session,
                score=float(item.get("score") or 0),
                state=str(item.get("state") or ""),
                timestamp=parsed_timestamp,
            )
        return Response(FocusSessionSerializer(focus_session).data, status=status.HTTP_201_CREATED)


class DashboardAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        stats, _ = LearnerStats.objects.get_or_create(user=request.user)
        skills_done = UserSkillProgress.objects.filter(user=request.user, is_done=True).count()
        projects_done = UserProjectLog.objects.filter(user=request.user).count()
        study_sessions = StudySession.objects.filter(user=request.user)
        total_study_minutes = study_sessions.aggregate(total=Sum("duration_minutes"))["total"] or 0
        today = timezone.localdate()
        today_study_minutes = study_sessions.filter(date=today).aggregate(total=Sum("duration_minutes"))["total"] or 0
        daily_breakdown = list(
            study_sessions.values("date")
            .annotate(total_minutes=Sum("duration_minutes"))
            .order_by("-date")[:7]
        )
        # Task stats
        tasks = Task.objects.filter(user=request.user)
        total_tasks = tasks.count()
        completed_tasks = tasks.filter(is_completed=True).count()
        latest_focus = FocusSession.objects.filter(user=request.user).order_by("-created_at").first()
        focus_summary = None
        if latest_focus:
            focus_summary = {
                "id": latest_focus.id,
                "status": latest_focus.status,
                "status_key": latest_focus.status_key,
                "avg_focus_score": latest_focus.avg_focus_score,
                "total_distractions": latest_focus.total_distractions,
                "duration_seconds": latest_focus.duration_seconds,
                "telemetry_points_count": latest_focus.telemetry_points_count,
                "created_at": latest_focus.created_at,
            }
        data = {
            "total_skills_done": skills_done,
            "total_projects_done": projects_done,
            "current_level": stats.current_level,
            "current_field_slug": stats.current_field_slug,
            "streak_days": stats.streak_days,
            "last_active": stats.last_active,
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
            "recent_sessions": StudySessionSerializer(study_sessions[:10], many=True).data,
            "focus_summary": focus_summary,
            "task_stats": {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "pending_tasks": total_tasks - completed_tasks,
                "completion_rate": int((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0,
            }
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


class TaskListAPI(APIView):
    """قائمة جميع مهام المستخدم مع إمكانية التصفية"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tasks = Task.objects.filter(user=request.user).order_by("-created_at")
        # تصفية حسب completed
        completed = request.query_params.get("completed")
        if completed is not None:
            is_completed = completed.lower() in ["true", "1", "yes"]
            tasks = tasks.filter(is_completed=is_completed)
        # تصفية حسب category
        category = request.query_params.get("category")
        if category:
            tasks = tasks.filter(category=category)
        return Response(TaskSerializer(tasks, many=True).data)

    def post(self, request):
        serializer = TaskSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        task = serializer.save()
        return Response(TaskSerializer(task).data, status=status.HTTP_201_CREATED)


class TaskDetailAPI(APIView):
    """تعديل أو حذف مهمة محددة"""
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        try:
            task = Task.objects.get(id=task_id, user=request.user)
        except Task.DoesNotExist:
            return Response({"detail": "المهمة غير موجودة"}, status=status.HTTP_404_NOT_FOUND)
        return Response(TaskSerializer(task).data)

    def patch(self, request, task_id):
        try:
            task = Task.objects.get(id=task_id, user=request.user)
        except Task.DoesNotExist:
            return Response({"detail": "المهمة غير موجودة"}, status=status.HTTP_404_NOT_FOUND)
        serializer = TaskSerializer(task, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        task = serializer.save()
        return Response(TaskSerializer(task).data)

    def delete(self, request, task_id):
        try:
            task = Task.objects.get(id=task_id, user=request.user)
        except Task.DoesNotExist:
            return Response({"detail": "المهمة غير موجودة"}, status=status.HTTP_404_NOT_FOUND)
        task.delete()
        return Response({"deleted": True})


class TaskToggleAPI(APIView):
    """تحديد مهمة كمكتملة/غير مكتملة"""
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        try:
            task = Task.objects.get(id=task_id, user=request.user)
        except Task.DoesNotExist:
            return Response({"detail": "المهمة غير موجودة"}, status=status.HTTP_404_NOT_FOUND)
        task.is_completed = not task.is_completed
        if task.is_completed:
            task.completed_at = timezone.now()
        else:
            task.completed_at = None
        task.save()
        return Response(TaskSerializer(task).data)


class TaskStatsAPI(APIView):
    """إحصائيات المهام للداشبورد"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tasks = Task.objects.filter(user=request.user)
        total_tasks = tasks.count()
        completed_tasks = tasks.filter(is_completed=True).count()
        pending_tasks = tasks.filter(is_completed=False).count()
        today = timezone.localdate()
        today_tasks = tasks.filter(target_date=today)
        today_completed = today_tasks.filter(is_completed=True).count()
        categories = tasks.values("category").annotate(
            count=Count("id"),
            completed=Count("id", filter=Q(is_completed=True))
        ).distinct()
        return Response({
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "pending_tasks": pending_tasks,
            "completion_rate": int((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0,
            "today_tasks": today_tasks.count(),
            "today_completed": today_completed,
            "categories": list(categories),
        })
