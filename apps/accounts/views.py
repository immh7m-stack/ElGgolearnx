from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.quizzes.models import Question, QuizAttempt

from .forms import ProfileForm


@login_required
def profile_view(request):
    profile = request.user.profile
    quiz_attempts = (
        QuizAttempt.objects.filter(user=request.user)
        .select_related("video_catalog")
        .order_by("-completed_at")[:6]
    )

    quiz_scores = [attempt.score for attempt in quiz_attempts if attempt.score is not None]
    average_score = round(sum(quiz_scores) / len(quiz_scores), 1) if quiz_scores else 0.0
    successful_attempts = sum(1 for attempt in quiz_attempts if attempt.score is not None and attempt.score >= 70)

    attempt_details = []
    for attempt in quiz_attempts:
        answers = attempt.user_answers or {}
        answered_questions = Question.objects.filter(catalog=attempt.video_catalog, id__in=[int(qid) for qid in answers.keys() if str(qid).isdigit()])
        question_map = {str(q.id): q for q in answered_questions}

        detailed_answers = []
        correct_count = 0
        for question_id, user_answer in answers.items():
            question = question_map.get(str(question_id))
            if not question:
                continue
            is_correct = str(user_answer).strip().lower() == str(question.correct_answer).strip().lower()
            if is_correct:
                correct_count += 1
            detailed_answers.append({
                "question_text": question.text,
                "user_answer": user_answer,
                "correct_answer": question.correct_answer,
                "is_correct": is_correct,
            })

        attempt_details.append(
            {
                "attempt": attempt,
                "correct_count": correct_count,
                "total_answers": len(detailed_answers),
                "detailed_answers": detailed_answers,
            }
        )

    if request.method == "POST":
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect("accounts:profile")
    else:
        form = ProfileForm(instance=profile)
    return render(
        request,
        "accounts/profile.html",
        {
            "form": form,
            "quiz_attempts": quiz_attempts,
            "average_score": average_score,
            "successful_attempts": successful_attempts,
            "attempt_details": attempt_details,
        },
    )


def auth_ui(request):
    """Render the standalone auth UI for design/testing."""
    return render(request, "account/auth.html", {})
