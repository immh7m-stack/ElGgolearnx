from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from apps.accounts.models import LearnerStats
from apps.quizzes.models import VideoQuizCatalog, Question, QuizAttempt
from apps.quizzes.serializers import (
    FetchOrGenerateRequestSerializer,
    QuizSubmissionRequestSerializer,
)
from apps.quizzes.services.ai_generator import fetch_or_generate_quizzes


def exam_detail(request, video_id):
    catalog = VideoQuizCatalog.objects.filter(video_id=video_id).first()
    if catalog is None:
        catalog = VideoQuizCatalog.objects.create(video_id=video_id, title=video_id)

    result = fetch_or_generate_quizzes(video_id=video_id, trigger_mode="on_demand")
    micro_questions = result.get("micro_questions", [])
    final_questions = result.get("final_questions", [])

    latest_attempt = None
    latest_answers = {}
    if request.user.is_authenticated:
        stats, _ = LearnerStats.objects.get_or_create(user=request.user)
        attempts = QuizAttempt.objects.filter(user=request.user, video_catalog=catalog).order_by("-completed_at")[:5]
        latest_attempt = attempts[0] if attempts else None
        if latest_attempt is not None:
            latest_answers = {
                str(key): value
                for key, value in (latest_attempt.user_answers or {}).items()
            }
    else:
        stats = None
        attempts = QuizAttempt.objects.none()

    for question in micro_questions + final_questions:
        question_id = str(question.get("id") or "")
        if question_id and question_id in latest_answers:
            answer = latest_answers[question_id]
            question["last_user_answer"] = answer
            question["last_is_correct"] = str(answer).strip().lower() == str(question.get("correct_answer", "")).strip().lower()
        else:
            question["last_user_answer"] = None
            question["last_is_correct"] = None

    return render(
        request,
        "exams/detail.html",
        {
            "video_id": video_id,
            "catalog": catalog,
            "micro_questions": micro_questions,
            "final_questions": final_questions,
            "attempts": attempts,
            "latest_attempt": latest_attempt,
            "stats": stats,
            "combined_questions": micro_questions + final_questions,
        },
    )


class FetchOrGenerateQuizView(APIView):
    """
    POST /api/quizzes/fetch-or-generate/
    Fetches stored video quizzes from SQLite cache or generates them via AI.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = FetchOrGenerateRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        video_id = serializer.validated_data["video_id"]
        trigger_mode = serializer.validated_data.get("trigger_mode", "auto")

        try:
            result = fetch_or_generate_quizzes(video_id=video_id, trigger_mode=trigger_mode)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SubmitQuizView(APIView):
    """
    POST /api/quizzes/submit/
    Submits user quiz answers, computes score percentage, and stores QuizAttempt.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = QuizSubmissionRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        video_id = serializer.validated_data["video_id"]
        answers = serializer.validated_data["answers"]

        try:
            catalog = VideoQuizCatalog.objects.get(video_id=video_id)
        except VideoQuizCatalog.DoesNotExist:
            return Response(
                {"status": "error", "message": f"No quiz catalog found for video_id: {video_id}"},
                status=status.HTTP_404_NOT_FOUND
            )

        questions = Question.objects.filter(catalog=catalog)
        if not questions.exists():
            return Response(
                {"status": "error", "message": "No questions available for this video"},
                status=status.HTTP_400_BAD_REQUEST
            )

        details = {}
        correct_count = 0
        total_questions = 0

        # Build mapping by string and int IDs
        question_map = {str(q.id): q for q in questions}

        for q_id_str, user_ans in answers.items():
            if q_id_str in question_map:
                q = question_map[q_id_str]
                total_questions += 1
                is_correct = (str(user_ans).strip().lower() == str(q.correct_answer).strip().lower())
                if is_correct:
                    correct_count += 1

                details[q_id_str] = {
                    "is_correct": is_correct,
                    "user_answer": user_ans,
                    "correct_answer": q.correct_answer,
                    "explanation": q.explanation
                }

        # Calculate percentage score
        score = round((correct_count / total_questions * 100.0), 2) if total_questions > 0 else 0.0

        # Save QuizAttempt and update learner progress
        user = request.user if request.user.is_authenticated else None
        attempt = QuizAttempt.objects.create(
            user=user,
            video_catalog=catalog,
            score=score,
            user_answers=answers
        )

        if user is not None:
            stats, _ = LearnerStats.objects.get_or_create(user=user)
            stats.last_active = timezone.localdate()
            stats.save(update_fields=["last_active"])

            if score >= 70:
                stats.streak_days = max(stats.streak_days, 1)
                stats.save(update_fields=["streak_days", "last_active"])

        return Response(
            {
                "status": "success",
                "score": score,
                "correct_count": correct_count,
                "total_answered": total_questions,
                "details": details
            },
            status=status.HTTP_200_OK
        )
