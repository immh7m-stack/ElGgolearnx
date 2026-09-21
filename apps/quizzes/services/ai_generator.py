import json
import logging
from typing import Dict, Any, List, Tuple
from django.conf import settings

from config.gemini_client import gemini_post_generate_content

try:
    from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
except ImportError:  # pragma: no cover - fallback for environments without the package
    YouTubeTranscriptApi = None
    TranscriptsDisabled = Exception
    NoTranscriptFound = Exception

from apps.quizzes.models import VideoQuizCatalog, Question
from apps.quizzes.services.text_compressor import compress_transcript

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert technical educator for developers.
Your task is to turn video transcripts into high-quality, practical quizzes that reinforce real understanding.

STRICT CONSTRAINTS:
1. Focus ONLY on deep technical concepts, problem-solving, pitfalls, trade-offs, architecture decisions, debugging patterns, and real-world decisions.
2. DO NOT ask trivial definition questions, surface-level recall questions, or generic "what is" questions.
3. Prefer scenario-based questions that test judgment, comparison, debugging, and best practices.
4. Make the questions useful for someone learning from a video, not just for memorization.
5. LANGUAGE RULE: Write question text and explanations in simple Arabic, BUT ALWAYS keep technical terms in English (e.g., "Back-end", "API", "Whisper model", "State Management", "Docker", "Microservices").
6. Create a balanced set: 4-6 micro questions tied to specific moments in the video, and 3-4 final questions that test the full understanding of the topic.
7. Each question should have exactly 4 options, one clearly correct answer, and a short explanation that teaches the learner why it is correct.
8. Keep the wording concise, practical, and aligned with what a learner would actually face while building or debugging software.
9. RETURN ONLY VALID JSON matching the provided schema. No markdown wrapping, no extra text.

OUTPUT JSON SCHEMA:
{
  "micro_questions": [
    {
      "timestamp_start": 300,
      "timestamp_end": 600,
      "text": "سؤال...",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "Option A",
      "explanation": "شرح السبب..."
    }
  ],
  "final_questions": [
    {
      "timestamp_start": 0,
      "timestamp_end": 0,
      "text": "سؤال تجميعي...",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "Option A",
      "explanation": "شرح السبب..."
    }
  ]
}
"""


def fetch_youtube_transcript(video_id: str) -> list:
    """Fetches transcript captions for a given YouTube video ID."""
    if YouTubeTranscriptApi is None:
        logger.warning("youtube-transcript-api is not installed; skipping transcript fetch for %s", video_id)
        return []

    try:
        # Try fetching Arabic or English transcripts
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        try:
            transcript = transcript_list.find_transcript(['ar', 'en'])
        except Exception:
            # Fallback to automatically generated or any available language transcript
            transcript = transcript_list.find_generated_transcript(['ar', 'en'])
        return transcript.fetch()
    except (TranscriptsDisabled, NoTranscriptFound) as e:
        logger.warning(f"No transcript found for video {video_id}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error fetching transcript for video {video_id}: {e}")
        # Try direct fetch as fallback
        try:
            return YouTubeTranscriptApi.get_transcript(video_id, languages=['ar', 'en'])
        except Exception:
            return []


def normalize_questions_payload(payload: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Normalize AI output into a stable schema with practical defaults."""
    if not isinstance(payload, dict):
        payload = {}

    def normalize_question(item: Any, fallback_prefix: str) -> Dict[str, Any] | None:
        if not isinstance(item, dict):
            return None

        text = str(item.get("text") or "").strip()
        if not text:
            return None

        normalized_text = text
        if normalized_text.lower() in {"سؤال", "question", f"{fallback_prefix.lower()}"}:
            return None

        if "سؤال" not in normalized_text:
            normalized_text = f"سؤال: {normalized_text}"

        options = item.get("options") or []
        if not isinstance(options, list):
            options = []
        normalized_options: List[str] = []
        for opt in options:
            opt_text = str(opt).strip()
            if opt_text:
                normalized_options.append(opt_text)
        while len(normalized_options) < 4:
            normalized_options.append(f"خيار {len(normalized_options) + 1}")
        normalized_options = normalized_options[:4]

        correct_answer = str(item.get("correct_answer") or "").strip()
        if not correct_answer or correct_answer not in normalized_options:
            correct_answer = normalized_options[0]

        explanation = str(item.get("explanation") or "").strip()
        if not explanation:
            explanation = "هذا الخيار الأنسب لأنه يربط المفهوم بالسيناريو العملي المعروض في الفيديو."

        return {
            "timestamp_start": int(item.get("timestamp_start") or 0),
            "timestamp_end": int(item.get("timestamp_end") or 0),
            "text": normalized_text,
            "options": normalized_options,
            "correct_answer": correct_answer,
            "explanation": explanation,
        }

    micro_questions = []
    for item in payload.get("micro_questions", []) or []:
        normalized = normalize_question(item, "سؤال دقيق")
        if normalized:
            micro_questions.append(normalized)

    final_questions = []
    for item in payload.get("final_questions", []) or []:
        normalized = normalize_question(item, "سؤال تجميعي")
        if normalized:
            final_questions.append(normalized)

    return {
        "micro_questions": micro_questions,
        "final_questions": final_questions,
    }


def generate_fallback_questions(video_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """Fallback generator when transcript or OpenAI API is unavailable."""
    return normalize_questions_payload({
        "micro_questions": [
            {
                "timestamp_start": 300,
                "timestamp_end": 600,
                "text": "ما الأفضل عند مواجهة مشكلة أداء في تطبيق ويب؟",
                "options": [
                    "تحليل السبب الجذري قبل تطبيق أي تحسين",
                    "إغلاق جميع الـ Logs",
                    "إيقاف قاعدة البيانات مؤقتاً",
                    "تغيير اسم المشروع"
                ],
                "correct_answer": "تحليل السبب الجذري قبل تطبيق أي تحسين",
                "explanation": "التحليل الجذري يساعد على اختيار الحل الأمثل بدلًا من تطبيق تحسينات عشوائية."
            }
        ],
        "final_questions": [
            {
                "timestamp_start": 0,
                "timestamp_end": 0,
                "text": "كيف تساعد الـ API Design الجيدة في تسهيل التطوير والتوسع؟",
                "options": [
                    "من خلال جعل التفاعل بين المكونات واضحاً وقابلاً للتوسع",
                    "بإخفاء الأخطاء عن المستخدم",
                    "بإلغاء الحاجة إلى الوثائق",
                    "بإيقاف الاختبارات"
                ],
                "correct_answer": "من خلال جعل التفاعل بين المكونات واضحاً وقابلاً للتوسع",
                "explanation": "تصميم الـ API الواضح يجعل النظام أكثر مرونة وأسهل في الصيانة والتوسع."
            }
        ]
    })


def call_openai_quiz_generator(compressed_transcript: str) -> Dict[str, Any]:
    """Uses OpenAI-compatible or Gemini-backed generation when configured, otherwise falls back to safe built-in questions."""
    api_key = getattr(settings, 'OPENAI_API_KEY', '')
    gemini_key = getattr(settings, 'GEMINI_API_KEY', '')

    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Generate quizzes from this video transcript:\n\n{compressed_transcript}"},
                ],
                temperature=0.3,
            )
            content = response.choices[0].message.content
            data = json.loads(content)
            return normalize_questions_payload(data)
        except Exception as e:
            logger.warning(f"OpenAI Generation Error: {e}")

    if gemini_key:
        try:
            payload = {
                "contents": [{
                    "parts": [{"text": f"{SYSTEM_PROMPT}\n\nGenerate quizzes from this video transcript:\n\n{compressed_transcript}"}]
                }],
                "generationConfig": {"responseMimeType": "application/json"},
            }
            response = gemini_post_generate_content(payload, timeout=60)
            if response and response.ok:
                content = response.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                if content:
                    parsed = json.loads(content)
                    return normalize_questions_payload(parsed)
        except Exception as e:
            logger.warning(f"Gemini Generation Error: {e}")

    logger.warning("No AI provider configured. Falling back to default questions.")
    return generate_fallback_questions("fallback")


def get_cached_quiz_data(catalog: VideoQuizCatalog) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Retrieves cached quiz questions from SQLite DB."""
    micro_qs = catalog.questions.filter(question_type='MICRO').order_by('timestamp_start')
    final_qs = catalog.questions.filter(question_type='FINAL').order_by('id')

    micro_data = [
        {
            "id": q.id,
            "timestamp_start": q.timestamp_start,
            "timestamp_end": q.timestamp_end,
            "text": q.text,
            "options": q.options,
            "correct_answer": q.correct_answer,
            "explanation": q.explanation
        }
        for q in micro_qs
    ]

    final_data = [
        {
            "id": q.id,
            "timestamp_start": q.timestamp_start,
            "timestamp_end": q.timestamp_end,
            "text": q.text,
            "options": q.options,
            "correct_answer": q.correct_answer,
            "explanation": q.explanation
        }
        for q in final_qs
    ]

    return micro_data, final_data


def fetch_or_generate_quizzes(video_id: str, trigger_mode: str = "auto") -> Dict[str, Any]:
    """
    Main pipeline entry point:
    1. Check SQLite DB permanent cache. Return stored quizzes immediately if present (0ms latency).
    2. Extract captions using youtube-transcript-api.
    3. Clean and compress text.
    4. Generate micro and final questions using OpenAI API in JSON mode.
    5. Save to SQLite database and return payload.
    """
    catalog, created = VideoQuizCatalog.objects.get_or_create(video_id=video_id)

    # 1. Permanent Cache Hit (0ms latency)
    has_questions = catalog.questions.exists()
    if catalog.is_generated and has_questions:
        micro_data, final_data = get_cached_quiz_data(catalog)
        return {
            "status": "success",
            "cached": True,
            "video_id": video_id,
            "micro_questions": micro_data,
            "final_questions": final_data,
            "final_questions_count": len(final_data)
        }

    # 2. Extract Transcript
    raw_transcript = fetch_youtube_transcript(video_id)

    # 3. Clean & Compress
    if raw_transcript:
        compressed_text = compress_transcript(raw_transcript)
    else:
        compressed_text = "General software engineering technical overview video."

    # 4. Generate via OpenAI API
    raw_questions = call_openai_quiz_generator(compressed_text)
    if not raw_questions.get("micro_questions") and not raw_questions.get("final_questions"):
        raw_questions = generate_fallback_questions(video_id)

    # 5. Persist to DB
    question_objects = []

    for item in raw_questions.get("micro_questions", []):
        question_objects.append(
            Question(
                catalog=catalog,
                question_type="MICRO",
                timestamp_start=item.get("timestamp_start", 0),
                timestamp_end=item.get("timestamp_end", 0),
                text=item.get("text", ""),
                options=item.get("options", []),
                correct_answer=item.get("correct_answer", ""),
                explanation=item.get("explanation", "")
            )
        )

    for item in raw_questions.get("final_questions", []):
        question_objects.append(
            Question(
                catalog=catalog,
                question_type="FINAL",
                timestamp_start=item.get("timestamp_start", 0),
                timestamp_end=item.get("timestamp_end", 0),
                text=item.get("text", ""),
                options=item.get("options", []),
                correct_answer=item.get("correct_answer", ""),
                explanation=item.get("explanation", "")
            )
        )

    Question.objects.bulk_create(question_objects)
    catalog.is_generated = True
    catalog.save()

    micro_data, final_data = get_cached_quiz_data(catalog)

    return {
        "status": "success",
        "cached": False,
        "video_id": video_id,
        "micro_questions": micro_data,
        "final_questions": final_data,
        "final_questions_count": len(final_data)
    }
