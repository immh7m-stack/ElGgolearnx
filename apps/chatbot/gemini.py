import logging
from dataclasses import dataclass

import requests
from django.conf import settings

from config.gemini_client import gemini_post_generate_content

logger = logging.getLogger(__name__)

# دليل ثابت للمنصة — يُعطي Gemini معلومات دقيقة عن الصفحات والمسارات (لا تبالغ في روابط خارجية).
PLATFORM_GUIDE_AR = """
أنت جزء من منصة **ElGgolearn** (إل جي جو ليرن): منصة عربية لتعلّم التقنية بالمسارات (Junior / Mid / Senior) وقوائم يوتيوب وكتب ومشاريع.

**أهم الصفحات والمسارات (مسارات URL تقريبية):**
- `/fields/` أو مسارات المجالات: عرض المجالات التقنية والمسارات المهنية لكل مستوى.
- مسار مسار محدد: `/fields/<slug>/tracks/<junior|mid|senior>/` — مهارات، مشاريع GitHub، قوائم تشغيل مرتبطة.
- وحدة داخل مسار: صفحات الوحدات التعليمية ضمن المسار.
- `/library/search/` — بحث عن كورسات يوتيوب (قوائم تشغيل) وكتب ومصادر؛ يمكن حفظ القوائم.
- `/library/my/` — مكتبة المستخدم: القوائم المحفوظة، الكتب، وتحميلات yt-dlp إن وُجدت.
- `/library/watch/` — مشاهدة قائمة تشغيل داخل الموقع (قد يُعطّل بعض القنوات التضمين؛ يوجد رابط لمشاهدة على يوتيوب).
- `/dashboard/` — لوحة التقدم والمهارات والمشاريع المكتملة وسلسلة أيام النشاط (streak) والمسار الحالي.
- `/plan/` — ElGoPlan: أهداف ومهام وربط مع مسارات المنصة، وتخزين محلي في المتصفح لأجزاء من الواجهة.
- `/accounts/profile/` أو ملف شخصي — الإعدادات والإحصائيات بحسب التطبيق.
- الشريط العلوي يربط معظم هذه الصفحات.

**سلوكك تجاه أسئلة «إيش المنصة؟» أو التوجيه:**
- اشرح بلغة عربية واضحة ومختصرة؛ وجّه المستخدم لصفحة مناسبة داخل المنصة عند الحاجة.
- إن كان السؤال تقنياً (برمجة، مفهوم)، أجب مباشرة مع الأمثلة كالمعتاد.
- لا تختلق ميزات غير مذكورة أعلاه؛ إذا لم تكن متأكدًا قل أن المنصة تتطور وأن الإعداد يعتمد على النشر الحالي.
"""


def _page_focus_ar(page_path: str) -> str:
    """وصف قصير للصفحة الحالية بناءً على المسار (بدون استعلام ?query)."""
    if not (page_path or "").strip():
        return ""
    path = page_path.strip().split("?")[0].lower().rstrip("/")
    if not path:
        return "المستخدم غالبًا في **الصفحة الرئيسية** أو نقطة دخول عامة للمنصة."
    # تعيينات جزئية — تغطي الأنماط الشائعة
    hints: list[tuple[str, str]] = [
        ("/library/search", "المستخدم في **صفحة بحث المكتبة**: بحث يوتيوب/كتب، بدء تحميلات، حفظ نتائج."),
        ("/library/my", "المستخدم في **مكتبته الشخصية**: قوائم محفوظة، عناصر مكتبة، حالة التحميلات."),
        ("/library/watch", "المستخدم في **مشغّل القائمة**: دروس يوتيوب؛ قد تحتاج الإجابة إلى ذكر التضمين أو فتح يوتيوب."),
        ("/library/history", "المستخدم في **سجلّ التصفّح/القوائم** المفتوحة سابقًا."),
        ("/library/sites", "المستخدم في **مواقع تعليمية موثّقة** على المنصة."),
        ("/plan", "المستخدم في **ElGoPlan** (التخطيط): أهداف، مهام، يوميات؛ البيانات قد تكون محفوظة محليًا في المتصفح."),
        ("/dashboard", "المستخدم في **لوحة التقدّم**: مهارات، مشاريع، streak، مسار حالي."),
        ("/fields", "المستخدم في منطقة **المسارات / المجالات** (Roadmaps)."),
        ("/accounts", "المستخدم في صفحات **الحساب** (تسجيل، ملف، إلخ)."),
        ("/community", "المستخدم في قسم **المجتمع** إن وُجد على هذا النشر."),
    ]
    # مطابقة أطول أولاً (بدون "/" الجذر لتجنب مطابقة خاطئة)
    hints_sorted = sorted(hints, key=lambda x: len(x[0]), reverse=True)
    for prefix, text in hints_sorted:
        if path == prefix or path.startswith(prefix + "/"):
            return text
    return f"المستخدم يتصفّح مسارًا عامًا في المنصة: `{page_path.strip()}` — أجب مع مراعاة أنه داخل ElGgolearn."


def build_system_prompt(context: dict) -> str:
    field_slug = context.get("field_slug", "") or ""
    track_level = context.get("track_level", "") or ""
    module_title = context.get("module_title", "") or ""
    page_path = context.get("page_path", "") or ""

    parts = [
        PLATFORM_GUIDE_AR.strip(),
        "",
        "مهمتك الأساسية كمساعد تعليمي: أجب بالعربية ما لم يطلب المتعلّم غير ذلك؛ كن مختصرًا وعمليًا؛ قدّم أمثلة كود عند الحاجة.",
    ]
    page_hint = _page_focus_ar(page_path)
    if page_hint:
        parts.extend(["", "**السياق الحالي للصفحة:**", page_hint])
    if field_slug or track_level or module_title:
        parts.append("")
        parts.append("**السياق الخاص بالمسار التعليمي الحالي (إن وُجد):**")
        if field_slug:
            parts.append(f"- المجال (slug): {field_slug}")
        if track_level:
            parts.append(f"- مستوى المسار: {track_level}")
        if module_title:
            parts.append(f"- عنوان الوحدة الحالية: {module_title}")
        parts.append(
            "- استخدم هذا السياق عندما يسأل عن «هذا المسار» أو «الوحدة» أو «ماذا بعد في التعلم هنا»."
        )
    else:
        parts.extend(
            [
                "",
                "**لا يوجد مسار تعليمي محدّد في الصفحة** — إذا سأل عن المنصة أو التنقل، اعتمد على دليل المنصة أعلاه.",
            ]
        )
    return "\n".join(parts)


RATE_LIMIT_MESSAGE_AR = (
    "النظام عليه ضغط حالياً، حاول تاني بعد دقيقة 🔄"
)


@dataclass
class GeminiChatResult:
    text: str
    rate_limit_exhausted: bool = False


def chat_with_gemini(messages: list[dict], context: dict) -> GeminiChatResult:
    api_key = getattr(settings, "GEMINI_API_KEY", "") or ""
    if not api_key:
        logger.warning("ElGgolearn chatbot: GEMINI_API_KEY is missing or empty after loading .env / api.env")
        return GeminiChatResult(
            text=(
                "مساعد الذكاء الاصطناعي غير مفعّل حالياً. "
                "أضف GEMINI_API_KEY في ملف .env (أو api.env) ثم أعد تشغيل السيرفر."
            ),
        )

    system = build_system_prompt(context)
    contents = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})

    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": contents,
    }

    try:
        resp = gemini_post_generate_content(payload, timeout=60)

        if resp.status_code == 429:
            logger.error(
                "Gemini API HTTP 429 after retries — model=%s",
                getattr(settings, "GEMINI_MODEL", ""),
            )
            return GeminiChatResult(text=RATE_LIMIT_MESSAGE_AR, rate_limit_exhausted=True)

        if not resp.ok:
            err_body = resp.text[:800] if resp.text else ""
            model = getattr(settings, "GEMINI_MODEL", "")
            logger.error(
                "Gemini API HTTP %s — model=%s — body snippet: %s",
                resp.status_code,
                model,
                err_body,
            )
            if resp.status_code == 401 or resp.status_code == 403:
                return GeminiChatResult(
                    text=(
                        "المفتاح غير صالح أو غير مصرّح (HTTP "
                        f"{resp.status_code}). راجع GEMINI_API_KEY في .env وما إذا كان المفتاح مفعّلاً لـ Generative Language API."
                    ),
                )
            if resp.status_code == 404:
                return GeminiChatResult(
                    text=(
                        "تعذّر الوصول لجميع نماذج Gemini المجرّبة (HTTP 404). تحقق من: "
                        "(1) المفتاح من Google AI Studio وليس مفتاحًا خاطئًا؛ "
                        "(2) في .env أو api.env عيّن GEMINI_MODEL=gemini-2.5-flash أو gemini-flash-latest؛ "
                        "(3) افتح https://aistudio.google.com/apikey وأنشئ مفتاحًا جديدًا إن لزم؛ "
                        "(4) أعد تشغيل السيرفر بعد الحفظ."
                    ),
                )
            return GeminiChatResult(text=f"خطأ من خادم Gemini (HTTP {resp.status_code}). تفاصيل في سجلات السيرفر.")

        data = resp.json()
        if "error" in data:
            logger.error("Gemini JSON error: %s", data["error"])
            msg = data["error"].get("message", str(data["error"]))
            return GeminiChatResult(text=f"رد غير متوقع من Gemini: {msg}")

        candidates = data.get("candidates") or []
        if not candidates:
            logger.error("Gemini returned no candidates: %s", str(data)[:500])
            return GeminiChatResult(
                text="لم يُرجع النموذج أي إجابة (قد يكون المحتوى محظوراً أو فارغاً). جرّب صياغة أقصر."
            )

        parts_out = candidates[0].get("content", {}).get("parts") or []
        if not parts_out or "text" not in parts_out[0]:
            return GeminiChatResult(text="تعذر قراءة نص الإجابة من Gemini.")
        return GeminiChatResult(text=parts_out[0]["text"])
    except requests.RequestException as e:
        logger.exception("Gemini network error: %s", e)
        return GeminiChatResult(text=f"فشل الاتصال بشبكة Gemini: {e}")
    except (KeyError, IndexError, TypeError) as e:
        logger.exception("Gemini parse error: %s", e)
        return GeminiChatResult(text=f"خطأ في معالجة رد Gemini: {e}")
